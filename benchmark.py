"""Token generation speed benchmark tool."""
import asyncio
import time
import aiohttp
import statistics
import json
from typing import List, Dict
import argparse


class TokenBenchmark:
    """Benchmark token generation speed."""

    def __init__(self, base_url: str = "http://127.0.0.1:8082"):
        self.base_url = base_url
        self.api_key = "sk-test"

    async def single_request(self, session: aiohttp.ClientSession, prompt: str = "Hi") -> Dict:
        """Send a single request and measure metrics."""
        request_id = str(hash(prompt))[:8]
        start_time = time.time()

        payload = {
            "model": "glm-5.1",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            async with session.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key
                },
                json=payload
            ) as response:
                first_byte_time = None
                content = ""
                chunk_count = 0
                token_count = 0

                async for line in response.content:
                    if first_byte_time is None:
                        first_byte_time = time.time()

                    line_str = line.decode('utf-8')
                    if line_str.strip():
                        chunk_count += 1

                        # Parse SSE format: data: {...}
                        if line_str.strip().startswith('data:'):
                            try:
                                data_start = line_str.index('data: ') + 6
                                json_str = line_str[data_start:].strip()
                                if json_str == '[DONE]':
                                    continue

                                data = json.loads(json_str)

                                # Handle Claude format: content_block_delta -> delta.text
                                if data.get('type') == 'content_block_delta':
                                    delta = data.get('delta', {})
                                    if delta.get('type') == 'text_delta':
                                        content += delta.get('text', '')

                                # Handle OpenAI format: choices[].delta.content
                                elif 'choices' in data and len(data['choices']) > 0:
                                    choice = data['choices'][0]
                                    if 'delta' in choice and 'content' in choice['delta']:
                                        content += choice['delta']['content']
                            except (json.JSONDecodeError, ValueError, KeyError):
                                pass

                end_time = time.time()

                # Calculate approximate token count (4 chars per token average)
                token_count = len(content) // 4 if content else 0

                return {
                    "request_id": request_id,
                    "success": response.status == 200,
                    "ttft_ms": (first_byte_time - start_time) * 1000 if first_byte_time else None,
                    "total_time_ms": (end_time - start_time) * 1000,
                    "total_time_s": end_time - start_time,
                    "chunk_count": chunk_count,
                    "token_count": token_count,
                    "tokens_per_second": token_count / (end_time - start_time) if end_time > start_time and token_count > 0 else 0,
                    "status": response.status
                }
        except Exception as e:
            end_time = time.time()
            return {
                "request_id": request_id,
                "success": False,
                "error": str(e),
                "total_time_s": end_time - start_time
            }

    async def benchmark_concurrent(self, concurrent_requests: int, total_requests: int, prompt: str = "Hello, please tell me a short joke"):
        """Run benchmark with concurrent requests."""
        print(f"[Starting] {concurrent_requests} concurrent, {total_requests} total requests")
        print(f"[Prompt] \"{prompt}\"")
        print(f"[Target] {self.base_url}")
        print("-" * 60)

        results = []
        start_time = time.time()
        completed = 0

        async with aiohttp.ClientSession() as session:
            while completed < total_requests:
                # Batch of concurrent requests
                batch_size = min(concurrent_requests, total_requests - completed)
                tasks = [self.single_request(session, prompt) for _ in range(batch_size)]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend([r for r in batch_results if r is not None])
                completed = len(results)

                # Progress
                if completed % 10 == 0 or completed == total_requests:
                    elapsed = time.time() - start_time
                    print(f"  Progress: {completed}/{total_requests} requests ({completed/elapsed:.1f} req/s)")

        total_time = time.time() - start_time

        # Calculate statistics
        successful = [r for r in results if r.get('success') and r.get('ttft_ms')]
        failed = [r for r in results if not r.get('success')]
        total_tokens = sum(r.get('token_count', 0) for r in successful)

        # Print results
        print("\n" + "=" * 60)
        print(" BENCHMARK RESULTS")
        print("=" * 60)

        print(f"\n  Overall Statistics:")
        print(f"  Total requests:      {total_requests}")
        print(f"  Successful:          {len(successful)}")
        print(f"  Failed:              {len(failed)}")
        print(f"  Total time:          {total_time:.1f}s")
        print(f"  Throughput:          {total_requests/total_time:.1f} requests/second")

        if successful:
            ttfts = [r['ttft_ms'] for r in successful if r.get('ttft_ms')]
            token_counts = [r['token_count'] for r in successful]
            tps_list = [r['tokens_per_second'] for r in successful if r.get('tokens_per_second', 0) > 0]

            print(f"\n Time to First Token (TTFT):")
            print(f"  Min:     {min(ttfts):.0f}ms" if ttfts else "  N/A")
            print(f"  Max:     {max(ttfts):.0f}ms" if ttfts else "  N/A")
            print(f"  Average: {statistics.mean(ttfts):.0f}ms" if ttfts else "  N/A")
            print(f"  Median:  {statistics.median(ttfts):.0f}ms" if ttfts else "  N/A")

            print(f"\n Token Generation:")
            print(f"  Total tokens:        {total_tokens}")
            print(f"  Avg tokens/req:      {statistics.mean(token_counts):.1f}" if token_counts else "  N/A")

            if tps_list:
                print(f"  Avg tokens/sec:      {statistics.mean(tps_list):.1f}")
                print(f"\n Token Speed:")
                print(f"  Min:     {min(tps_list):.1f} tokens/s")
                print(f"  Max:     {max(tps_list):.1f} tokens/s")
                print(f"  Median:  {statistics.median(tps_list):.1f} tokens/s")

        if failed:
            print(f"\n Failed Requests: {len(failed)}")
            for f in failed[:5]:
                print(f"  - {f.get('error', 'Unknown error')[:80]}")
            if len(failed) > 5:
                print(f"  ... and {len(failed) - 5} more")

        print("=" * 60)

        return {
            "total_requests": total_requests,
            "successful": len(successful),
            "failed": len(failed),
            "total_time_s": total_time,
            "throughput_rps": total_requests / total_time,
            "avg_ttft_ms": statistics.mean(ttfts) if ttfts else None,
            "avg_tokens_per_sec": statistics.mean(tps_list) if successful else None,
            "total_tokens": total_tokens
        }


async def main():
    parser = argparse.ArgumentParser(description="Benchmark token generation speed")
    parser.add_argument("-u", "--url", default="http://127.0.0.1:8082", help="Proxy URL")
    parser.add_argument("-c", "--concurrent", type=int, default=1, help="Concurrent requests")
    parser.add_argument("-n", "--number", type=int, default=10, help="Total requests")
    parser.add_argument("-p", "--prompt", default="Tell me a short joke", help="Test prompt")
    parser.add_argument("--warmup", type=int, default=2, help="Warmup requests")

    args = parser.parse_args()

    benchmark = TokenBenchmark(args.url)

    # Warmup
    if args.warmup > 0:
        print(f"[Warming up] {args.warmup} requests...")
        async with aiohttp.ClientSession() as session:
            for _ in range(args.warmup):
                await benchmark.single_request(session, "Hi")
        print("Warmup complete!\n")

    # Run benchmark
    await benchmark.benchmark_concurrent(args.concurrent, args.number, args.prompt)


if __name__ == "__main__":
    asyncio.run(main())
