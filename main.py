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

    # 保留旧指令 hahaha，同时提供中文指令。部分平台会在唤醒阶段移除
    # 前缀斜杠，因此同时兼容带斜杠和不带斜杠的写法。
    @filter.command("hahaha", alias={"搜图", "/搜图", "/hahaha"})
    async def hahaha(
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
            params, preferred_sizes = self._build_hahaha_params(
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
            image_components = []
            async with aiohttp.ClientSession(
                timeout=timeout,
                trust_env=True,
                headers={"User-Agent": "Mozilla/5.0 (AstrBot-AstobotPlugin)"},
            ) as image_session:
                for image in data[: int(num)]:
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
                    image_components.append(Comp.Image.fromBytes(image_bytes))
            if not image_components:
                raise ValueError("API 未返回有效图片")
            yield event.chain_result(image_components)
        except (aiohttp.ClientError, aiohttp.ContentTypeError, asyncio.TimeoutError) as exc:
            logger.warning(f"hahaha 指令请求 Lolicon API 失败: {exc}")
            yield event.plain_result("获取图片失败，请稍后再试。")
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning(f"hahaha 指令解析 API 响应失败: {exc}")
            yield event.plain_result("图片服务返回了无效数据，请稍后再试。")

    @staticmethod
    def _build_hahaha_params(r18, num, uid, keyword, tag, size, proxy,
                             dateAfter, dateBefore, dsc, excludeAI, aspectRatio):
        """将自动解析的参数转换为 API 查询参数。"""
        values = {
            "r18": r18, "num": num, "uid": uid, "keyword": keyword,
            "tag": tag, "size": size, "proxy": proxy,
            "dateAfter": dateAfter, "dateBefore": dateBefore,
            "dsc": dsc, "excludeAI": excludeAI, "aspectRatio": aspectRatio,
        }
        # 允许 /hahaha tag=派蒙：框架按位置传入第一个参数时不会再触发 int 转换错误。
        if isinstance(r18, str) and "=" in r18:
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
        return params, [x.strip() for x in str(size).split(",") if x.strip()]

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
