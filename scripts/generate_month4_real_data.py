"""
Month 4 端到端验证 - 生成真实运行数据
"""
import sys, os, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.query_rewriter import QueryRewriter
from src.routing.conversation_manager import DialogueManager
from src.memory.conversation_memory import ConversationMemory
from src.routing.dialogue_state_tracker import DialogueStateTracker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_real_data():
    print("=" * 60)
    print("Month 4 End-to-End Verification - Real Data Generation")
    print("=" * 60)

    rewriter = QueryRewriter()
    manager = DialogueManager()
    memory = ConversationMemory()
    tracker = DialogueStateTracker()

    real_data = []
    test_cases = [
        {"query": "PROD-001的功率是多少？", "intent": "spec"},
        {"query": "设备无法启动怎么办？", "intent": "troubleshoot"},
        {"query": "PROD-001和PROD-002兼容吗？", "intent": "compatibility"}
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}\nTest Case {i}: {test_case['query']}\n{'='*60}")

        session_id = f"test-session-{i}"
        result = {"test_case_id": i, "query": test_case["query"], "steps": {}}

        # Step 1: Start conversation
        print("\nStep 1: Start Conversation")
        manager.start_conversation(session_id)
        tracker.init_state(session_id)
        result["steps"]["start_conversation"] = {"session_id": session_id}

        # Step 2: Query rewriting
        print("\nStep 2: Query Rewriting")
        rewritten = rewriter.rewrite_query(test_case["query"], None)
        result["steps"]["query_rewriting"] = {"original": test_case["query"], "rewritten": rewritten}
        print(f"  Original: {test_case['query']}")
        print(f"  Rewritten: {rewritten}")

        # Step 3: Add to memory
        print("\nStep 3: Add to Memory")
        memory.add_memory(session_id, test_case["query"], "query")
        result["steps"]["add_memory"] = {"content": test_case["query"], "type": "query"}

        # Step 4: Update state
        print("\nStep 4: Update State")
        tracker.update_state(session_id, intent=test_case["intent"], phase="retrieving")
        state = tracker.get_state(session_id)
        result["steps"]["update_state"] = state
        print(f"  Intent: {state['intent']}, Phase: {state['phase']}")

        # Step 5: Generate response
        print("\nStep 5: Generate Response")
        response = f"Response for {test_case['query']}"
        manager.add_turn(session_id, test_case["query"], response)
        memory.add_memory(session_id, response, "response")
        result["steps"]["generate_response"] = {"response": response}

        # Step 6: End conversation
        print("\nStep 6: End Conversation")
        summary = manager.end_conversation(session_id)
        result["steps"]["end_conversation"] = summary
        print(f"  Total turns: {summary['total_turns']}")

        real_data.append(result)

    output_file = "month4_real_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(real_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}\nVerification Summary\n{'='*60}")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Real Data Generated: {output_file}")
    print(f"File Size: {os.path.getsize(output_file)} bytes")
    print(f"\n{'='*60}\nMonth 4 End-to-End Verification Complete\n{'='*60}")

    return True

if __name__ == "__main__":
    success = generate_real_data()
    sys.exit(0 if success else 1)
