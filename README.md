# AstobotPlugin

一个用于 AstrBot 的随机插画搜图插件，通过 [Lolicon API](https://api.lolicon.app/) 获取图片并发送到当前会话。

## 安装

1. 将本插件目录放入 AstrBot 的 `data/plugins` 目录。
2. 重启 AstrBot，或在插件管理器中重新加载插件。
3. 确认运行环境可以访问 `https://api.lolicon.app`。

## 使用

发送以下指令获取图片：

```text
/soutu
```

支持使用 `key=value` 或 `--key value` 形式传递参数。常用参数如下：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `r18` | 内容级别，通常为 `0` 或 `1` | `0` |
| `num` | 请求图片数量（当前发送第一张） | `1` |
| `uid` | 画师 UID，多个值用逗号分隔 | 无 |
| `keyword` | 关键词 | 无 |
| `tag` | 标签，多个值用逗号分隔 | 无 |
| `size` | 图片尺寸，如 `original`、`regular`，多个值用逗号分隔 | `original` |
| `proxy` | 图片代理地址 | 无 |
| `dateAfter` / `dateBefore` | 日期筛选（Unix 时间戳） | `0` |
| `dsc` | 按日期倒序，`true`/`false` | `false` |
| `excludeAI` | 排除 AI 生成图片，`true`/`false` | `false` |
| `aspectRatio` | 宽高比筛选，如 `1:1` | 无 |

示例：

```text
/soutu tag=猫娘,girl size=regular,original num=2
/soutu keyword=初音未来 excludeAI=true
/soutu --tag 风景 --size original
```

数组参数 `uid`、`tag`、`size` 使用英文逗号（`,`）分隔。插件会先下载图片，再上传到会话，适配无法直接读取远程图片链接的平台。

## 说明

- 图片由第三方 Lolicon API 提供，接口或网络异常时会提示稍后重试。
- 请遵守当地法律法规、平台规则以及图片服务的使用条款，并自行配置合适的内容过滤策略。

## 相关链接

- [AstrBot 项目](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档（中文）](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Development Docs (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)
