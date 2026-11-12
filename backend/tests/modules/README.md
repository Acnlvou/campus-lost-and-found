# 业务服务层测试

直接调用 `app/modules/*/service.py` 中的函数，跳过 HTTP 层，
用最小的准备数据验证业务规则本身：可见性、状态机、权限归属、审计副作用。

| 文件 | 被测函数 |
| --- | --- |
| `test_auth_service.py` | `authenticate` |
| `test_items_service.py` | `query_items`、`list_locations`、`publish_item`、`review_item` |
| `test_claims_service.py` | `submit_claim`、`review_claim` |

约定：

- 通过 `db` 夹具拿到与接口共享同一测试库的会话，用 `item_factory` / `claim_factory` 准备数据。
- 业务异常统一用 `BusinessError.status` + `message` 断言，不依赖 HTTP 状态码映射。
- 每个用例只验证一条规则，失败时能直接读出是哪条规则被破坏。
