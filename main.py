import asyncio
import aiohttp
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

@register("AstobotPlugin", "d-a-i-o-o", "AstobotPlugin 插件", "1.0.0")
class MyPlugin(Star):
    LOLICON_API = "https://api.lolicon.app/setu/v2"

    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 提供 soutu 和中文指令。部分平台会在唤醒阶段移除前缀斜杠，
    # 因此同时兼容带斜杠和不带斜杠的写法。
    @filter.command("soutu", alias={"搜图", "/搜图", "/soutu"})
    async def soutu(
        self,
        event: AstrMessageEvent,
        r18: str = "0",
        num: str = "1",
        uid: str = "",
        keyword: str = "",
        tag: str = "",
        size: str = "original",
        proxy: str = "",
        dateAfter: str = "0",
        dateBefore: str = "0",
        dsc: str = "false",
        excludeAI: str = "false",
        aspectRatio: str = "",
    ):
        """获取图片；参数按 Lolicon API 顺序填写，均为可选。"""
        try:
            params, preferred_sizes, image_count = self._build_soutu_params(
                r18, num, uid, keyword, tag, size, proxy,
                dateAfter, dateBefore, dsc, excludeAI, aspectRatio,
            )
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(
                timeout=timeout,
                trust_env=True,
                headers={"User-Agent": "AstrBot-AstobotPlugin/1.0"},
            ) as session:
                async with session.get(
                    self.LOLICON_API,
                    params=params,
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)

            if not isinstance(payload, dict):
                raise ValueError("API 返回的数据格式不正确")
            if payload.get("error"):
                raise ValueError(str(payload["error"]))

            data = payload.get("data")
            if not isinstance(data, list) or not data:
                raise ValueError("API 未返回图片数据")
            # 先下载图片再发送，兼容 QQ 官方等无法直接拉取远程图片链接的平台。
            image_messages = []
            async with aiohttp.ClientSession(
                timeout=timeout,
                trust_env=True,
                headers={"User-Agent": "Mozilla/5.0 (AstrBot-AstobotPlugin)"},
            ) as image_session:
                for image in data[:image_count]:
                    if not isinstance(image, dict):
                        raise ValueError("API 返回的图片数据格式无效")
                    urls = image.get("urls", {}) if isinstance(image, dict) else {}
                    image_url = next(
                        (urls.get(size) for size in preferred_sizes if isinstance(urls, dict) and urls.get(size)),
                        urls.get("original") if isinstance(urls, dict) else None,
                    )
                    if not isinstance(image_url, str) or not image_url.startswith(("http://", "https://")):
                        raise ValueError("API 返回的图片链接无效")
                    async with image_session.get(image_url) as image_response:
                        image_response.raise_for_status()
                        image_bytes = await image_response.read()
                    if not image_bytes:
                        raise ValueError("图片内容为空")
                    image_messages.append((
                        image.get("pid", "未知"),
                        image.get("title", "未知"),
                        image.get("author", "未知"),
                        Comp.Image.fromBytes(image_bytes),
                    ))
            if not image_messages:
                raise ValueError("API 未返回有效图片")
            # QQ 官方单条消息只支持一张图片，因此逐张发送；其他平台也能正常处理。
            for pid, title, author, image_component in image_messages:
                metadata = (
                    f"pid: {pid}\n"
                    f"标题: {title}\n"
                    f"作者: {author}"
                )
                yield event.chain_result([Comp.Plain(metadata), image_component])
        except (aiohttp.ClientError, aiohttp.ContentTypeError, asyncio.TimeoutError) as exc:
            logger.warning(f"soutu 指令请求 Lolicon API 失败: {exc}")
            yield event.plain_result("获取图片失败，请稍后再试。")
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning(f"soutu 指令解析 API 响应失败: {exc}")
            yield event.plain_result("图片服务返回了无效数据，请稍后再试。")

    @staticmethod
    def _build_soutu_params(r18, num, uid, keyword, tag, size, proxy,
                             dateAfter, dateBefore, dsc, excludeAI, aspectRatio):
        """将自动解析的参数转换为 API 查询参数。"""
        values = {
            "r18": r18, "num": num, "uid": uid, "keyword": keyword,
            "tag": tag, "size": size, "proxy": proxy,
            "dateAfter": dateAfter, "dateBefore": dateBefore,
            "dsc": dsc, "excludeAI": excludeAI, "aspectRatio": aspectRatio,
        }
        # 框架按位置传入参数时，/搜图 tag=派蒙 num=3 可能分别落入
        # r18 和 num；统一扫描所有参数，避免将 ``num=3`` 直接转 int。
        if any(isinstance(item, str) and "=" in item for item in values.values()):
            values = {k: "" for k in values}
            values.update({"r18": "0", "num": "1", "size": "original", "dsc": "false", "excludeAI": "false"})
            for item in (r18, num, uid, keyword, tag, size, proxy, dateAfter, dateBefore, dsc, excludeAI, aspectRatio):
                if isinstance(item, str) and "=" in item:
                    key, value = item.split("=", 1)
                    if key in values:
                        values[key] = value
            r18 = values["r18"]
            num = values["num"]
            uid = values["uid"]
            keyword = values["keyword"]
            tag = values["tag"]
            size = values["size"]
            proxy = values["proxy"]
            dateAfter = values["dateAfter"]
            dateBefore = values["dateBefore"]
            dsc = values["dsc"]
            excludeAI = values["excludeAI"]
            aspectRatio = values["aspectRatio"]
        # 兼容部分旧版框架未进入上面的批量解析分支：数字参数仍可能带有
        # ``num=``/``r18=`` 前缀，转换前剥离键名。
        if isinstance(r18, str) and r18.startswith("r18="):
            r18 = r18.split("=", 1)[1]
        if isinstance(num, str) and num.startswith("num="):
            num = num.split("=", 1)[1]
        r18, num = int(r18), int(num)
        dateAfter, dateBefore = int(dateAfter or 0), int(dateBefore or 0)
        dsc = str(dsc).lower() in {"1", "true", "yes"}
        excludeAI = str(excludeAI).lower() in {"1", "true", "yes"}
        params: list[tuple[str, object]] = [
            ("r18", r18), ("num", num),
            # aiohttp 查询参数不接受 bool，Lolicon API 接受 true/false 字符串。
            ("dsc", "true" if dsc else "false"),
            ("excludeAI", "true" if excludeAI else "false"),
        ]
        for name, value in (("keyword", keyword), ("proxy", proxy), ("aspectRatio", aspectRatio)):
            if value:
                params.append((name, value))
        for name in ("dateAfter", "dateBefore"):
            value = locals()[name]
            if value:
                params.append((name, value))
        for name, value in (("uid", uid), ("tag", tag), ("size", size)):
            for item in str(value).split(","):
                if item.strip():
                    params.append((name, int(item) if name == "uid" else item.strip()))
        return (
            params,
            [x.strip() for x in str(size).split(",") if x.strip()],
            num,
        )

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
