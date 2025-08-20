"""Performance benchmarks and testing utilities."""
import time
import asyncio
from typing import List, Dict, Any
from pathlib import Path
import json

def benchmark_canvas_requests(client, course_id: int, iterations: int = 10) -> Dict[str, float]:
    """Benchmark Canvas API request performance."""
    results = {}
    
    # Test list operations
    start = time.time()
    for _ in range(iterations):
        client.list_assignments(course_id)
    results['list_assignments'] = (time.time() - start) / iterations
    
    start = time.time() 
    for _ in range(iterations):
        client.list_modules(course_id)
    results['list_modules'] = (time.time() - start) / iterations
    
    start = time.time()
    for _ in range(iterations):
        client.list_pages(course_id)
    results['list_pages'] = (time.time() - start) / iterations
    
    return results

async def benchmark_async_requests(async_client, course_id: int) -> Dict[str, float]:
    """Benchmark async Canvas client performance."""
    results = {}
    
    # Sequential requests
    start = time.time()
    await async_client.get(f'/api/v1/courses/{course_id}/assignments')
    await async_client.get(f'/api/v1/courses/{course_id}/modules') 
    await async_client.get(f'/api/v1/courses/{course_id}/pages')
    results['sequential'] = time.time() - start
    
    # Concurrent requests
    start = time.time()
    await asyncio.gather(
        async_client.get(f'/api/v1/courses/{course_id}/assignments'),
        async_client.get(f'/api/v1/courses/{course_id}/modules'),
        async_client.get(f'/api/v1/courses/{course_id}/pages')
    )
    results['concurrent'] = time.time() - start
    
    return results

def profile_intent_parsing(dispatcher, test_requests: List[str]) -> Dict[str, float]:
    """Profile intent parsing performance."""
    results = {}
    
    # Fast parsing
    start = time.time()
    for request in test_requests:
        dispatcher._fast_intent_parse_optimized(request, [])
    results['fast_parsing'] = (time.time() - start) / len(test_requests)
    
    return results

def run_performance_suite(output_file: str = "performance_results.json"):
    """Run complete performance test suite."""
    print("🚀 Running CanvasAgent performance benchmarks...")
    
    results = {
        'timestamp': time.time(),
        'version': '2.0.0',
        'benchmarks': {}
    }
    
    # Test requests for parsing
    test_requests = [
        "create quiz about physics due tomorrow in course 123",
        "make assignment homework 1 worth 50 points in course 456", 
        "list assignments for course 123",
        "create page about syllabus in course 789",
        "upload file test.pdf to course 123"
    ]
    
    # Mock dispatcher for parsing tests
    class MockDispatcher:
        def _fast_intent_parse_optimized(self, request, courses):
            # Simulate parsing logic
            time.sleep(0.001)  # 1ms simulation
            return {}
    
    dispatcher = MockDispatcher()
    parsing_results = profile_intent_parsing(dispatcher, test_requests)
    results['benchmarks']['intent_parsing'] = parsing_results
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Performance results saved to {output_file}")
    return results

if __name__ == '__main__':
    run_performance_suite()
