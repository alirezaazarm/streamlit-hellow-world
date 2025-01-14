from init import client
import time
import json
from assistant_functions import add_order_row

def wait_for_runs_to_complete(thread_id):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ["requires_action", "processing"]:
            # Wait until the active run is completed with exponential backoff
            max_attempts = 5
            for attempt in range(max_attempts):
                time.sleep(2**attempt)  # Exponential backoff
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run.status in ["completed", "failed"]:
                    break
            else:
                print(f"Run {run.id} still active after {max_attempts} attempts.")

def run_assistant(thread_id, assistant_id):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ["requires_action", "processing"]:
            # Wait until the active run is completed
            while run.status not in ["completed", "failed"]:
                time.sleep(2)  # Polling interval
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    # Create a new run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

        if run.status == "requires_action":
            required_actions = run.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []

            for tool_call in required_actions["tool_calls"]:
                func_name = tool_call['function']['name']
                arguments = json.loads(tool_call['function']['arguments'])

                if func_name == "add_order_row":
                    required_params = ['first_name', 'last_name', 'address', 'phone', 'product', 'price', 'how_many']
                    missing_params = [param for param in required_params if param not in arguments]

                    if missing_params:
                        raise KeyError(f"Missing required parameters: {', '.join(missing_params)}")

                    output_df = add_order_row(
                        file_path="./drive/orders.json",
                        first_name=arguments['first_name'],
                        last_name=arguments['last_name'],
                        address=arguments['address'],
                        phone=arguments['phone'],
                        product=arguments['product'],
                        price=arguments['price'],
                        how_many=arguments['how_many']
                    )
                    tool_outputs.append({
                        "tool_call_id": tool_call['id'],
                        "output": output_df.to_json(orient='records', force_ascii=False)
                    })
                else:
                    raise ValueError(f"Unknown function: {func_name}")

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        elif run.status == "completed":
            break
        elif run.status == "failed":
            raise Exception(f"Run failed: {run.last_error}")
        else:
            print(f"Run status: {run.status}")
            time.sleep(2)  # Polling interval

    # Fetch messages after the run is completed
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data
