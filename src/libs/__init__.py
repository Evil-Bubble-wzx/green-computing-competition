"""
可插拔 RAG 层 (Pluggable RAG Layer)

四大 Provider，每种都遵循 "Base → Implementation → Factory" 三层结构:

  1. LLM        — 大模型对话 (DeepSeek)
  2. Embedding  — 文本向量化 (Qwen)
  3. Reranker   — 检索重排序 (LLM Reranker)
  4. Web Search — 联网搜索 (Builtin)

新增 Provider 三步:
  1. 继承 Base 类，实现接口
  2. 在 _register_providers() 中注册
  3. 在 settings.yaml 中切换 provider 名称
"""
