# 本地业务数据

`app.db` 是由 `output/<run_id>` 中的真实运行结果建立的本地 SQLite 业务索引。
数据库文件属于本机运行数据，不提交 Git；历史批次仍以 `output` 文件系统证据为准，
可使用 `python -m src.data_store` 幂等重建索引。
