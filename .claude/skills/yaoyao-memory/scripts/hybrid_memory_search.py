#!/usr/bin/env python3
"""
Hybrid Memory Search - 混合记忆搜索
结合 LLM_GLM5 + Qwen3-Embedding + FTS 实现多层级记忆检索
"""

import json
import sys
import os
import subprocess
import urllib.request
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional

# 路径配置
VECTORS_DB = Path.home() / ".openclaw" / "memory-tdai" / "vectors.db"
VEC_EXT = "/home/tiamo/.openclaw/extensions/memory-tencentdb/node_modules/sqlite-vec-linux-x64/vec0"

# API 配置 - 从环境变量或配置文件读取
GITEE_API = "https://ai.gitee.com/v1/embeddings"
GITEE_KEY = os.environ.get("GITEE_AI_KEY", "")
GLM5_URL = os.environ.get("GLM5_API_URL", "https://celia-claw-drcn.ai.dbankcloud.cn/celia-claw/v1/sse-api/chat/completions")
GLM5_KEY = os.environ.get("GLM5_API_KEY", "")
GLM5_UID = os.environ.get("GLM5_UID", "")


class EmbeddingClient:
    """Qwen3-Embedding 客户端"""
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本向量"""
        data = json.dumps({
            "input": text,
            "model": "Qwen3-Embedding-8B",
            "dimensions": 4096
        }).encode('utf-8')
        
        req = urllib.request.Request(
            GITEE_API,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GITEE_KEY}"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['data'][0]['embedding']
        except Exception as e:
            print(f"Embedding API 错误: {e}")
            return None


class LLMClient:
    """LLM_GLM5 客户端"""
    
    def chat(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """调用 GLM5"""
        data = {
            "model": "LLM_GLM5",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": True
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "x-request-from": "openclaw",
            "x-uid": GLM5_UID,
            "x-api-key": GLM5_KEY
        }
        
        try:
            req = urllib.request.Request(
                GLM5_URL,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            full_content = ""
            with urllib.request.urlopen(req, timeout=120) as resp:
                for line in resp:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str:
                            try:
                                chunk = json.loads(data_str)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        full_content += content
                            except:
                                continue
            
            return full_content if full_content else None
        except Exception as e:
            print(f"LLM API 错误: {e}")
            return None
    
    def expand_query(self, query: str) -> List[str]:
        """使用 LLM 扩展查询"""
        prompt = f"""请将以下查询扩展为3-5个相关搜索词，用于记忆检索。
每行一个搜索词，不要编号，不要解释。

查询: {query}

搜索词:"""
        
        response = self.chat(prompt, max_tokens=200)
        if response:
            terms = [line.strip() for line in response.strip().split('\n') if line.strip()]
            return terms[:5]
        return [query]
    
    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """使用 LLM 重排序结果"""
        if not results:
            return results
        
        results_text = "\n".join([
            f"{i+1}. [{r['type']}] {r['content'][:80]}..."
            for i, r in enumerate(results[:10])
        ])
        
        prompt = f"""请根据查询对以下记忆结果进行相关性排序。
返回排序后的编号列表（用逗号分隔），例如: 3,1,5,2,4

查询: {query}

记忆结果:
{results_text}

排序:"""
        
        response = self.chat(prompt, max_tokens=100)
        if response:
            try:
                order = [int(x.strip()) - 1 for x in response.split(',') if x.strip().isdigit()]
                if order and max(order) < len(results):
                    return [results[i] for i in order if i < len(results)]
            except:
                pass
        
        return results


class VectorSearch:
    """向量搜索"""
    
    def search_l1_vector(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """向量搜索 L1 记忆"""
        # 将向量转换为 hex
        vec_hex = struct.pack(f'{len(query_embedding)}f', *query_embedding).hex()
        
        # vec0 需要使用 MATCH 和 k 参数
        sql = f"""
SELECT v.record_id, r.content, r.type, r.scene_name, r.priority, v.distance
FROM l1_vec v
JOIN l1_records r ON v.record_id = r.record_id
WHERE v.embedding MATCH X'{vec_hex}' AND k = {top_k + 10}
ORDER BY v.distance ASC;
"""
        
        cmd = ['sqlite3', '-cmd', f'.load {VECTORS_DB.replace('"', '')}', VECTORS_DB, sql]
        
        try:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print(f"向量搜索错误: {result.stderr[:200]}")
                return []
            
            lines = result.stdout.strip().split('\n')
            results = []
            for line in lines:
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 6:
                        record_id, content, mem_type, scene, priority, distance = parts[:6]
                        try:
                            dist = float(distance)
                            if dist > 0:
                                results.append({
                                    "record_id": record_id,
                                    "content": content,
                                    "type": mem_type,
                                    "scene": scene,
                                    "priority": int(priority) if priority.isdigit() else 50,
                                    "distance": dist,
                                    "score": 1.0 - dist,
                                    "source": "vector"
                                })
                        except:
                            continue
            
            return results[:top_k]
        except Exception as e:
            print(f"向量搜索失败: {e}")
            return []
    
    def search_fts(self, query: str, top_k: int = 5) -> List[Dict]:
        """FTS5 全文搜索"""
        # 分词
        tokens = query.replace('，', ' ').replace('、', ' ').split()
        fts_query = " OR ".join(tokens)
        
        sql = f"""
SELECT record_id, content, type, scene_name, priority
FROM l1_fts
WHERE l1_fts MATCH '{fts_query}'
ORDER BY rank
LIMIT {top_k};
"""
        
        cmd = ['sqlite3', VECTORS_DB, sql]
        
        try:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return []
            
            lines = result.stdout.strip().split('\n')
            results = []
            for line in lines:
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        record_id, content, mem_type, scene, priority = parts[:5]
                        results.append({
                            "record_id": record_id,
                            "content": content,
                            "type": mem_type,
                            "scene": scene,
                            "priority": int(priority) if priority.isdigit() else 50,
                            "source": "fts"
                        })
            
            return results
        except Exception as e:
            print(f"FTS 搜索失败: {e}")
            return []


class HybridMemorySearch:
    """混合记忆搜索"""
    
    def __init__(self):
        self.embedding_client = EmbeddingClient()
        self.llm_client = LLMClient()
        self.vector_search = VectorSearch()
    
    def search(self, query: str, top_k: int = 5, use_llm: bool = True) -> Dict[str, Any]:
        """混合搜索"""
        results = {
            "query": query,
            "expanded_terms": [],
            "vector_results": [],
            "fts_results": [],
            "merged_results": [],
            "llm_reranked": []
        }
        
        # 1. LLM 查询扩展
        if use_llm:
            print("🔍 LLM 查询扩展...")
            expanded = self.llm_client.expand_query(query)
            results["expanded_terms"] = expanded
            print(f"   扩展词: {', '.join(expanded)}")
        
        # 2. 向量搜索
        print("🔍 向量搜索...")
        embedding = self.embedding_client.get_embedding(query)
        if embedding:
            vec_results = self.vector_search.search_l1_vector(embedding, top_k * 2)
            results["vector_results"] = vec_results
            print(f"   找到 {len(vec_results)} 条向量结果")
        
        # 3. FTS 搜索
        print("🔍 全文搜索...")
        fts_results = self.vector_search.search_fts(query, top_k * 2)
        results["fts_results"] = fts_results
        print(f"   找到 {len(fts_results)} 条 FTS 结果")
        
        # 4. 合并结果
        print("🔄 合并结果...")
        merged = self._merge_results(
            results["vector_results"],
            results["fts_results"],
            top_k * 2
        )
        results["merged_results"] = merged
        
        # 5. LLM 重排序
        if use_llm and merged:
            print("🔄 LLM 重排序...")
            reranked = self.llm_client.rerank_results(query, merged)
            results["llm_reranked"] = reranked[:top_k]
        else:
            results["llm_reranked"] = merged[:top_k]
        
        return results
    
    def _merge_results(self, vec_results: List[Dict], fts_results: List[Dict], top_k: int) -> List[Dict]:
        """合并结果"""
        seen = set()
        merged = []
        
        for r in vec_results:
            if r["record_id"] not in seen:
                merged.append(r)
                seen.add(r["record_id"])
        
        for r in fts_results:
            if r["record_id"] not in seen:
                merged.append(r)
                seen.add(r["record_id"])
        
        merged.sort(key=lambda x: (x.get("priority", 50), x.get("score", 0)), reverse=True)
        
        return merged[:top_k]


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 hybrid_memory_search.py '<查询>' [--no-llm]")
        print("示例: python3 hybrid_memory_search.py '用户偏好设置'")
        sys.exit(1)
    
    query = sys.argv[1]
    use_llm = "--no-llm" not in sys.argv
    
    print("=" * 50)
    print("混合记忆搜索")
    print("=" * 50)
    print(f"查询: {query}")
    print(f"LLM 增强: {'启用' if use_llm else '禁用'}")
    print()
    
    searcher = HybridMemorySearch()
    results = searcher.search(query, top_k=5, use_llm=use_llm)
    
    print("\n" + "=" * 50)
    print("搜索结果")
    print("=" * 50)
    
    if results["llm_reranked"]:
        for i, r in enumerate(results["llm_reranked"], 1):
            print(f"\n{i}. [{r['type']}] (优先级: {r.get('priority', 'N/A')})")
            print(f"   场景: {r.get('scene', 'N/A')}")
            print(f"   内容: {r['content'][:100]}...")
            print(f"   来源: {r.get('source', 'N/A')}")
            if 'score' in r:
                print(f"   相似度: {r['score']:.4f}")
    else:
        print("未找到相关记忆")


if __name__ == "__main__":
    main()
