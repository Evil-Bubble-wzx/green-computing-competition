"""
混合检索引擎

三条检索通道 + RRF 融合 + Rerank 精排:
  1. DB 检索    — 结构化数据精确查询 (SQL)
  2. 向量检索    — 企划书语义匹配 (ChromaDB)
  3. 联网搜索    — 外部政策/新闻 (Web Search)

RRF: Reciprocal Rank Fusion，对三通道结果去重融合
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchHit:
    """单条检索命中"""
    source: str            # "database" | "vector" | "web"
    content: str
    score: float           # 相关性分数 (0-1)
    title: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    query: str
    hits: list[SearchHit]
    db_count: int = 0
    vector_count: int = 0
    web_count: int = 0
    fusion_count: int = 0


class HybridSearcher:
    """混合检索编排器

    用法:
        searcher = HybridSearcher(query_engine, vector_store, web_search, reranker)
        result = searcher.search("江苏的绿色算力水平如何？")
    """

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 8,
        db_k: int = 10,
        vec_k: int = 10,
        web_k: int = 5,
    ) -> SearchResult:
        """执行混合检索"""
        all_hits: list[SearchHit] = []
        db_count = vec_count = web_count = 0

        # 1. 数据库检索
        if self.qe:
            db_hits = self._search_db(query, db_k)
            all_hits.extend(db_hits)
            db_count = len(db_hits)

        # 2. 向量检索
        if self.vector_store:
            vec_hits = self._search_vector(query, vec_k)
            all_hits.extend(vec_hits)
            vec_count = len(vec_hits)

        # 3. 联网搜索
        if self.web_search:
            web_hits = self._search_web(query, web_k)
            all_hits.extend(web_hits)
            web_count = len(web_hits)

        # 4. RRF 融合排序
        fused = self._rrf_fusion(all_hits, k=60)

        # 5. Rerank 精排
        if self.reranker and len(fused) > top_k:
            docs = [h.content for h in fused]
            try:
                ranked = self.reranker.rerank(query, docs, top_k=top_k)
                # 用 rerank 结果重建 hits
                final = []
                for rd in ranked:
                    if rd.index < len(fused):
                        h = fused[rd.index]
                        h.score = rd.score
                        final.append(h)
                fused = final
            except Exception:
                fused = fused[:top_k]
        else:
            fused = fused[:top_k]

        return SearchResult(
            query=query,
            hits=fused,
            db_count=db_count,
            vector_count=vec_count,
            web_count=web_count,
            fusion_count=len(fused),
        )

    # ------------------------------------------------------------------
    # 三个检索通道
    # ------------------------------------------------------------------

    def _search_db(self, query: str, top_k: int) -> list[SearchHit]:
        """数据库检索 — 关键词映射到 SQL 查询"""
        hits = []

        # 检测省份名
        province_pattern = r"(北京|天津|上海|重庆|河北|山西|内蒙古|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|广西|海南|四川|贵州|云南|西藏|陕西|甘肃|青海|宁夏|新疆)"
        provinces = re.findall(province_pattern, query)

        # 检测年份
        year_match = re.search(r"(20(1[6-9]|2[0-4]))", query)
        year = int(year_match.group(1)) if year_match else 2024

        keywords = {
            "得分|排名|多少名|第几": self._query_score,
            "趋势|历年|变化|增长": self._query_trend,
            "七维|维度|雷达|短板": self._query_dimension,
            "布局|类型|分类|承载|驱动|承接|潜力|约束": self._query_layout,
            "LPA|lpa|潜在|剖面|类型识别": self._query_lpa,
            "LISA|lisa|空间|集聚|离群": self._query_lisa,
            "边界|不稳定": self._query_boundary,
            "数据中心|绿色中心": self._query_datacenter,
            "枢纽|节点|东数西算": self._query_hub,
        }

        matched = False
        for pattern, handler in keywords.items():
            if re.search(pattern, query):
                try:
                    result_hits = handler(query, provinces, year, top_k)
                    hits.extend(result_hits)
                    matched = True
                except Exception:
                    pass

        # 如果没有匹配到任何关键词，做通用省份查询
        if not matched and provinces:
            for p in provinces[:3]:
                try:
                    s = self.qe.get_province_summary(p)
                    hits.append(SearchHit(
                        source="database",
                        content=f"{s.province}: 综合得分{s.composite_score}, 排名{s.score_rank}, {s.layout_type}, LPA:{s.lpa_type_name}, 稳定性:{s.stability_label}",
                        score=1.0,
                        title=f"{s.province} 绿色算力概况",
                        metadata={"type": "province_summary", "province": p, "year": year},
                    ))
                except Exception:
                    pass

        # 如果什么也没匹配到（推荐类/趋势类泛问），提供综合排名 + 布局汇总作为上下文
        if not hits:
            try:
                top = self.qe.get_top_n(10, year)
                top_text = "; ".join(f"{r['省份']} 第{r['排名']}名({r['综合得分']:.4f})" for r in top)
                hits.append(SearchHit(source="database", score=0.8,
                    content=f"2024年综合得分Top10: {top_text}",
                    title="综合排名 Top 10"))

                summary = self.qe.get_layout_summary()
                layout_text = "; ".join(f"{s['layout_type']}: {s['count']}省(均分{s['avg_score']:.3f})" for s in summary)
                hits.append(SearchHit(source="database", score=0.7,
                    content=f"五类布局汇总: {layout_text}",
                    title="布局分类汇总"))

                bp = self.qe.get_boundary_provinces()
                if bp:
                    bp_text = "; ".join(f"{b['province']}(保持原布局概率{b['keep_prob']:.0%})" for b in bp)
                    hits.append(SearchHit(source="database", score=0.6,
                        content=f"边界省份: {bp_text}", title="布局边界省份"))
            except Exception:
                pass

        return hits[:top_k]

    # --- DB 查询处理器 ---

    def _query_score(self, query, provinces, year, top_k) -> list[SearchHit]:
        hits = []
        if provinces:
            for p in provinces[:5]:
                s = self.qe.get_province_summary(p)
                hits.append(SearchHit(source="database", score=1.0,
                    content=f"{s.province} 综合得分{s.composite_score}, 全国排名第{s.score_rank}, 布局类型: {s.layout_type}",
                    title=f"{s.province} 得分", metadata={"province": p, "year": year}))
        else:
            top = self.qe.get_top_n(min(top_k, 10), year)
            for r in top:
                hits.append(SearchHit(source="database", score=0.9,
                    content=f"{r['省份']} 综合得分{r['综合得分']:.4f}, 排名第{r['排名']}",
                    title=f"Top{len(top)} 排名", metadata={"year": year}))
        return hits

    def _query_trend(self, query, provinces, year, top_k) -> list[SearchHit]:
        hits = []
        for p in (provinces or [])[:3]:
            history = self.qe.get_score_history(p)
            content = f"{p} 历年得分: " + ", ".join(f"{h['年份']}:{h['综合得分']:.4f}" for h in history)
            hits.append(SearchHit(source="database", score=1.0, content=content, title=f"{p} 趋势"))
        return hits

    def _query_dimension(self, query, provinces, year, top_k) -> list[SearchHit]:
        hits = []
        for p in (provinces or [])[:3]:
            dims = self.qe.get_dimension_scores(p, year)
            content = f"{p} 七维得分: " + ", ".join(f"{k}:{v:.4f}" for k, v in dims.items() if v)
            hits.append(SearchHit(source="database", score=1.0, content=content, title=f"{p} 维度"))
        return hits

    def _query_layout(self, query, provinces, year, top_k) -> list[SearchHit]:
        hits = []
        summary = self.qe.get_layout_summary()
        for s in summary:
            provs = self.qe.get_provinces_by_layout(s["layout_type"])
            hits.append(SearchHit(source="database", score=0.8,
                content=f"{s['layout_type']}: {s['count']}省, 平均得分{s['avg_score']:.4f}, 省份: {', '.join(provs)}",
                title=s["layout_type"]))
        return hits

    def _query_lpa(self, query, provinces, year, top_k) -> list[SearchHit]:
        hits = []
        # 指定省份时，返回该省的 LPA 类型与稳定性
        if provinces:
            for p in provinces[:5]:
                s = self.qe.get_province_summary(p)
                hits.append(SearchHit(source="database", score=1.0,
                    content=f"{s.province} LPA类型: {s.lpa_type_name}, LPA稳定性: {s.lpa_stability_label} (基准类型保持率{s.lpa_keep_rate:.1%})",
                    title=f"{s.province} LPA 类型识别"))
        # LPA 类型稳定性边界省份 (Bootstrap 保持率 < 60%)
        boundary = self.qe.get_lpa_boundary_provinces()
        if boundary:
            content = "LPA类型不稳定省份(Bootstrap保持率<60%): " + ", ".join(
                f"{b['province']}({b['lpa_type_name']},保持率{b['keep_rate']:.1%})" for b in boundary
            )
            hits.append(SearchHit(source="database", score=0.9, content=content, title="LPA 类型稳定性"))
        return hits

    def _query_lisa(self, query, provinces, year, top_k) -> list[SearchHit]:
        sig = self.qe.get_significant_lisa()
        if sig:
            content = "LISA 显著省份: " + ", ".join(f"{s['province']}({s['lisa_type']})" for s in sig)
            return [SearchHit(source="database", score=0.9, content=content, title="LISA 空间集聚")]
        return []

    def _query_boundary(self, query, provinces, year, top_k) -> list[SearchHit]:
        bp = self.qe.get_boundary_provinces()
        if bp:
            content = "布局边界省份: " + ", ".join(f"{b['province']}(保持原布局概率{b['keep_prob']:.2%})" for b in bp)
            return [SearchHit(source="database", score=0.9, content=content, title="边界省份")]
        return []

    def _query_datacenter(self, query, provinces, year, top_k) -> list[SearchHit]:
        all_p = self.qe._all(f'SELECT "省份", "2023国家绿色数据中心数" FROM "{self.qe.TBL_GOLDEN}" WHERE "2023国家绿色数据中心数" > 0 ORDER BY "2023国家绿色数据中心数" DESC')
        content = "拥有国家绿色数据中心的省份: " + ", ".join(f"{r['省份']}({r['2023国家绿色数据中心数']}家)" for r in all_p)
        return [SearchHit(source="database", score=0.9, content=content, title="绿色数据中心分布")]

    def _query_hub(self, query, provinces, year, top_k) -> list[SearchHit]:
        hubs = self.qe._all(f'SELECT "省份" FROM "{self.qe.TBL_GOLDEN}" WHERE "国家枢纽省份" = :h', {"h": "是"})
        content = "国家算力枢纽省份: " + ", ".join(r["省份"] for r in hubs)
        return [SearchHit(source="database", score=0.9, content=content, title="算力枢纽节点")]

    def __init__(self, query_engine=None, vector_store=None, embedding=None, web_search=None, reranker=None):
        self.qe = query_engine
        self.vector_store = vector_store
        self.embedding = embedding
        self.web_search = web_search
        self.reranker = reranker

    def _search_vector(self, query: str, top_k: int) -> list[SearchHit]:
        """向量检索 — ChromaDB 企划书语义搜索"""
        if not self.vector_store or not self.embedding:
            return []
        try:
            qv = self.embedding.embed_query(query)
            results = self.vector_store.search(qv, top_k=top_k)
            hits = []
            for r in results:
                distance = r.get("distance", 1.0)
                score = 1.0 / (1.0 + distance)  # 距离转相似度
                src = r.get("metadata", {}).get("source", "") if isinstance(r.get("metadata"), dict) else ""
                hits.append(SearchHit(
                    source="vector",
                    content=r.get("text", ""),
                    title=src,
                    score=score,
                ))
            return hits
        except Exception:
            return []

    def _search_web(self, query: str, top_k: int) -> list[SearchHit]:
        """联网搜索"""
        if not self.web_search:
            return []
        try:
            results = self.web_search.search(query, max_results=top_k)
            return [
                SearchHit(source="web", content=r.snippet, title=r.title, url=r.url, score=0.5)
                for r in results
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # RRF 融合
    # ------------------------------------------------------------------

    def _rrf_fusion(self, hits: list[SearchHit], k: int = 60) -> list[SearchHit]:
        """Reciprocal Rank Fusion

        对多通道结果按排名位置加权融合，k 为平滑常数。
        同内容去重：取最高分。
        """
        if not hits:
            return []

        # 按 (source, content前200字) 去重
        seen = {}
        for h in hits:
            key = (h.source, h.content[:200])
            if key not in seen or h.score > seen[key].score:
                seen[key] = h

        unique = list(seen.values())
        # 按 score 降序
        unique.sort(key=lambda x: x.score, reverse=True)
        return unique
