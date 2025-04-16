import requests, time, json, re, os, argparse; from datetime import datetime
from multiprocessing import Pool, cpu_count, Manager

parser = argparse.ArgumentParser()
parser.add_argument('model_name', type=str, help='Name of the model')
args = parser.parse_args()
model_name_passed = args.model_name

#llama3.2:3b, gemma3 did BEST
#also exaone3.5:2.4b GREAT Total Syllabi: 4 | Total Success MCQ : 4 MCQ
#qwen2.5:1.5b FASTEST got ALL CORRECT in ONE GO
current_model = model_name_passed
max_attempts_can = 2
total_success_mcq = 0
syllabus_counter = 1
parallel_processes_count = 2

#load subjects
with open('shorter_subjects.json', 'r') as file:
    subject_entries = json.load(file) 

total_syllabi = len(subject_entries)

def sanitize_filename(name):
    return name.replace(":", "-")

def print_and_log(message=""):
    # Sanitize model name
    safe_model_name = sanitize_filename(current_model)
    
    # Create the logs directory path
    logs_dir = os.path.join(os.getcwd(), "model_logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create file name based on sanitized model name and current time (hour, day, month)
    timestamp = datetime.now().strftime("%m-%d-%H")
    filename = f"{safe_model_name}_{timestamp}.txt"
    file_path = os.path.join(logs_dir, filename)

    #log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S  ")
    log_time=""
    full_message = f"{log_time}{message}"

    # Print to console
    print(full_message)

    # Append to log file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

# Build the few-shot prompt generator
def build_locked_format_prompt_syllabus(entry):
    example = (
        "Prompt: Syllabus for Cambridge Grade 5 Mathematics, topic fractions, subtopic fraction addition\n"
        "Response: Syllabus for Cambridge Grade 5 Mathematics - Fractions - Fraction Addition:\n"
        "- Introduction to fractions as parts of a whole\n"
        "- Understanding numerators and denominators\n"
        "- Adding fractions with the same denominator\n"
        "- Adding fractions with different denominators\n"
        "- Simplifying fractions after addition\n"
        "- Solving word problems involving fraction addition\n"
    )

    new_prompt = (
        f"Prompt: Syllabus for {entry['board']} Grade {entry['grade']} {entry['subject']}, "
        f"topic {entry['topic']}, subtopic {entry['sub_topic']}\n"
        "Response:"
    )

    final_prompt = (
        "You are a succint syllabus generator. Don't create more than 5 to 8 different points. Follow the exact formatting style as shown below:\n\n"
        f"{example}\n"
        "Do not deviate from this structure. Do not add any titles, headings, or explanations. END IT AFTER CREATING THE SYLLABUS\n\n"
        f"{new_prompt}"
    )

    return final_prompt

def build_locked_format_prompt_mcq_json(syllabus_text, warning_message="", expected_mcq=8):
    example = """Prompt: Generate 2 MCQs for each line of the syllabus below. Generate TOTAL 14 MCQs.

Syllabus for CBSE Grade 12 Chemistry - Organic Chemistry: Alcohols, Phenols, Ethers:
- Structure and Nomenclature of Alcohols
- Properties and Reactions of Alcohols
- Formation of Phenols from Alcohols
- Synthesis Methods of Phenols
- Physical Properties of Ethers
- Reaction Mechanisms and Synthesis of Ethers
- Comparative Study: Alcohols, Phenols, Ethers

Response:
[
    {"q_no": "1", "question": "Which functional group defines alcohols?", "options": {"a": "Carbonyl (-CO-)", "b": "Hydroxyl (-OH)", "c": "Nitrile (-CN)", "d": "Carboxyl (-COOH)"}, "correct_answer": "Hydroxyl (-OH)"},
    {"q_no": "2", "question": "Which property is NOT typically associated with alcohols due to their -OH group?", "options": {"a": "Miscibility with water", "b": "High boiling points", "c": "Formation of esters via dehydration", "d": "High reactivity towards halogens"}, "correct_answer": "Formation of esters via dehydration"},
    {"q_no": "3", "question": "What is the product formed when phenol undergoes dehydration?", "options": {"a": "Phenoxide ion", "b": "Ethanol", "c": "Ethylbenzene", "d": "Phenyl acetic acid"}, "correct_answer": "Phenoxide ion"},
    {"q_no": "4", "question": "Ethers are classified based on the nature of their alkyl groups bonded to oxygen. Which term refers to ethers with two alkyl groups?", "options": {"a": "Monoethers", "b": "Diethers", "c": "Triethers", "d": "Polyethers"}, "correct_answer": "Diethers"},
    {"q_no": "5", "question": "Which of the following is NOT a reaction type generally involved in alcohol chemistry?", "options": {"a": "Oxidation", "b": "Hydration", "c": "Reduction", "d": "Halogenation"}, "correct_answer": "Reduction"},
    {"q_no": "6", "question": "Phenols exhibit increased reactivity compared to alcohols due to which property?", "options": {"a": "Presence of a lone pair on oxygen", "b": "Presence of a triple bond", "c": "Higher molecular weight", "d": "Absence of any reactive group"}, "correct_answer": "Presence of a lone pair on oxygen"},
    {"q_no": "7", "question": "Which alcohol derivative forms ethers through nucleophilic substitution?", "options": {"a": "Methanol", "b": "Ethanol", "c": "Dimethyl ether", "d": "Propanol"}, "correct_answer": "Methanol"},
    {"q_no": "8", "question": "Comparing alcohols, phenols, and ethers, which one exhibits acidic properties due to resonance stabilization?", "options": {"a": "Alcohols", "b": "Phenols", "c": "Ethers", "d": "Carboxylic acids"}, "correct_answer": "Phenols"},
    {"q_no": "9", "question": "Which alcohol derivative would show significant solubility in nonpolar solvents due to lack of polar functional groups?", "options": {"a": "Ethanol", "b": "Propanol", "c": "Butanol", "d": "Methanol"}, "correct_answer": "Butanol"},
    {"q_no": "10", "question": "What functional group characterizes ethers?", "options": {"a": "Hydrogen bonding", "b": "-OR", "c": "-NH2", "d": "-CN"}, "correct_answer": "-OR"},
    {"q_no": "11", "question": "What type of reaction would likely be performed to synthesize ethers from alcohols?", "options": {"a": "Hydrogenation", "b": "Dehydration", "c": "Hydrolysis", "d": "Substitution"}, "correct_answer": "Dehydration"},
    {"q_no": "12", "question": "Which characteristic distinguishes phenols from alcohols in terms of reactivity towards electrophiles?", "options": {"a": "Increased stability due to resonance", "b": "Lower reactivity due to no lone pairs", "c": "Higher reactivity due to resonance", "d": "Lower reactivity due to no double bonds"}, "correct_answer": "Increased stability due to resonance"},
    {"q_no": "13", "question": "Which alcohol derivative typically shows a significant difference in boiling points compared to non-polar alcohols due to intermolecular hydrogen bonding?", "options": {"a": "Ethanol", "b": "Methanol", "c": "Diethyl ether", "d": "Propanol"}, "correct_answer": "Ethanol"},
    {"q_no": "14", "question": "In comparing alcohols, phenols, and ethers, which exhibits high reactivity towards nucleophiles due to the presence of oxygen?", "options": {"a": "Ethers", "b": "Phenols", "c": "Alcohols", "d": "Carboxylic acids"}, "correct_answer": "Phenols"}
]
"""

    prompt = f"""
You are an expert at creating educational MCQs & following instructions to the point.

REQUIREMENTS:
- Generate exactly {expected_mcq} MCQs.
- Do not include any THING ELSE, no explanations or markdown formatting, ONLY the JSON.
- The output must be a single JSON array.
- Stop outputting once the last JSON object is written.

Absolutely avoid the following json formatting mistakes in all cases:
- Incorrect JSON Format: Do NOT use any extra characters or incorrect placement of commas. Ensure that each JSON entry is properly enclosed in curly braces, and that the entire list is enclosed in square brackets.
- Improper Quotation Marks: Use standard double quotes (") for all strings and keys. Avoid any other kinds of quotation marks (like curly quotes or single quotes).
- Empty or Broken JSON: The JSON must be a complete array with no missing elements or incomplete entries.
Always check the json structure thoroughly before returning your response.

Possible Additional Warnings to absolutely avoid:
{warning_message}


Here is an example to guide the output format:

{example}

Prompt: Generate 2 MCQs for each line of the syllabus below. Generate TOTAL {expected_mcq} MCQs.

{syllabus_text}

Response:
"""
    
    #print("\n==========================\nPROMPT GOTTEN\n")
    #print(prompt.strip())
    #print("\n==========================END PROMPT GOTTEN\n")

    return prompt.strip()

def clean_json_output(output):
    # Remove the "```json" block from the beginning and "```" from the end
    cleaned_output = re.sub(r'```json\s*|\s*```', '', output).strip()
    return cleaned_output

def generate_response(own_prompt, error_count, error_lock):
    start = time.time()
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": current_model,
            "prompt": own_prompt,
            "stream": False
            #"top_k": 32,
            #"top_p": 0.80
        })

        time_took = time.time() - start

        try:
            response_json = response.json()
        except Exception as e:
            with error_lock:
                error_count.value += 1
            return {
                "response_text": json.dumps({ "error": f"❌ JSON decode error: {str(e)}" }),
                "time_took": round(time_took, 3),
                "token_gen_speed": 0,
                "total_tokens": 0
            }

        # Safely check for key
        if "response" not in response_json:
            with error_lock:
                error_count.value += 1
            return {
                "response_text": json.dumps({
                    "error": f"❌ API response missing 'response' key. Got: {response_json}",
                    "status_code": response.status_code
                }),
                "time_took": round(time_took, 3),
                "token_gen_speed": 0,
                "total_tokens": 0
            }

        response_text = response_json["response"]
        approx_tokens = len(response_text.split())
        token_gen_speed = approx_tokens / time_took if time_took > 0 else 0

        return {
            "response_text": clean_json_output(response_text),
            "time_took": round(time_took, 3),
            "token_gen_speed": round(token_gen_speed, 3),
            "total_tokens": approx_tokens
        }

    except requests.exceptions.RequestException as e:
        with error_lock:
                error_count.value += 1
        return {
            "response_text": json.dumps({"error": f"❌ Request FAILED from GET GO!!!: {str(e)}"}),
            "time_took": round(time.time() - start, 3),
            "token_gen_speed": 0,
            "total_tokens": 0
        }

def generate_syllabus_response(entry, error_count, error_lock):
    syllabus_prompt = build_locked_format_prompt_syllabus(entry)
    return generate_response(syllabus_prompt, error_count, error_lock)

def generate_mcq_response(syllabus_text, syllabus_index, error_count, error_lock):
    global total_success_mcq

    max_attempts = max_attempts_can
    # Extracting bullet points from the syllabus
    #print_and_log("📝📝📝 GOTTEN SYLLABUS 📝📝📝")
    #print_and_log(syllabus_text)
    #print_and_log()

    bullet_points = [line for line in syllabus_text.split("\n") if line.strip().startswith("-") and len(line.strip()) > 1]
    bullet_count = len(bullet_points)

    expected_mcqs = bullet_count * 2  # 2 MCQs per bullet point
    print_and_log("🚀🚀🚀 EXPECTED MCQs: " + str(expected_mcqs))

    attempts = 0
    longest_valid_response = None  # Start with None to indicate no valid response has been found

    mcq_prompt = build_locked_format_prompt_mcq_json(syllabus_text, expected_mcq=expected_mcqs)

    warning_message = ""

    while attempts < max_attempts:
        attempts += 1
        print_and_log(f"Attempt {attempts}/{max_attempts} for Syllabus {syllabus_index + 1} of {total_syllabi}... | {current_model}\n")

        start = time.time()
        generated_mcq_response = generate_response(mcq_prompt, error_count, error_lock)
        time_taken = time.time()-start

        print_and_log(f"🔍🔍🔍 Generated MCQ:\n\n {generated_mcq_response["response_text"]}")
        print_and_log(f"Time Taken: {time_taken:.2f} seconds | Tokens Produced: {generated_mcq_response["total_tokens"]} | ⚡⚡⚡ Token Speed {(generated_mcq_response["total_tokens"]/time_taken):.3f} tokens/sec")

        # Try parsing the response as JSON and check if it meets the expected criteria
        try:
            # Extract the response text and try to parse it as JSON
            jsoned_mcqs = json.loads(generated_mcq_response["response_text"])

            # Check if the number of MCQs is as expected
            if len(jsoned_mcqs) >= expected_mcqs:
                total_success_mcq += 1
                print_and_log(f"✅✅✅ Successfully generated {len(jsoned_mcqs)} MCQs. Attempts Needed {attempts}")
                return generated_mcq_response
            else:
                with error_lock:
                    error_count.value += 1
                # Update the longest valid response if the current response is valid and has more MCQs
                if longest_valid_response is None or len(jsoned_mcqs) > len(json.loads(longest_valid_response["response_text"])):
                    longest_valid_response = generated_mcq_response

                warning_message += f"⚠️ Warning: Expected {expected_mcqs} MCQs but got {len(jsoned_mcqs)}...\n"
                print_and_log(warning_message)
                mcq_prompt = build_locked_format_prompt_mcq_json(syllabus_text, warning_message, expected_mcq=expected_mcqs)

        except json.JSONDecodeError as e:
            with error_lock:
                error_count.value += 1
            warning_message += f"⚠️ Error: Invalid JSON format...\n"
            print_and_log(warning_message)
            mcq_prompt = build_locked_format_prompt_mcq_json(syllabus_text, warning_message, expected_mcq=expected_mcqs)

    # After {attempts} attempts, return the longest valid JSON response if it exists
    if longest_valid_response:
        print_and_log(f"⚠️ Warning: After {attempts} attempts returning longest valid response.")
        return longest_valid_response

    # If no valid responses were generated, return a failure message
    return {
        "response_text": json.dumps({ "error": f"❌ Error: Failed to generate valid MCQs after {attempts} attempts.", "attempts": attempts}),
        "time_took": 0,
        "token_gen_speed": 0,
        "total_tokens": 0
    }

def syllabus_and_mcq(new_syllabus, syllabus_index, error_count, error_lock):
    tokens_gen = 0
    start = time.time()

    generated_full_syllabus = generate_syllabus_response(new_syllabus, error_count, error_lock)
    tokens_gen += generated_full_syllabus["total_tokens"]

    print_and_log(f'📝📝📝 GOTTEN SYLLABUS {syllabus_index + 1} of {total_syllabi} 📝📝📝')
    gotten_syllabus = generated_full_syllabus['response_text']
    print_and_log(gotten_syllabus)
    print_and_log(f"TIME for SYLLABUS: {generated_full_syllabus['time_took']} | ⚡⚡⚡ Token Speed: {generated_full_syllabus['token_gen_speed']} tokens/sec\n")

    # Extract only bullet lines
    generated_full_mcq = generate_mcq_response(gotten_syllabus, syllabus_index, error_count, error_lock)
    tokens_gen += generated_full_mcq["total_tokens"]

    #decode mcq to json
    gotten_mcq_jsoned = json.loads(generated_full_mcq['response_text'])

    print_and_log(f'👏👏👏  FINAL MCQ  👏👏👏 for Syllabus {syllabus_index + 1} of {total_syllabi}')
    print_and_log(json.dumps(gotten_mcq_jsoned, indent=3))
    print_and_log(f"TIME for MCQ: {generated_full_mcq['time_took']} | ⚡⚡⚡ Token Speed: {generated_full_mcq['token_gen_speed']} tokens/sec")
    print_and_log(f"TOTAL Tokens for Syllabus {syllabus_index+1} & its MCQ: {tokens_gen} | TOTAL Time: {(time.time() - start):.2f}\n")

    return {
        "syllabus_no": syllabus_index+1,
        "syllabus": gotten_syllabus,
        "MCQ": gotten_mcq_jsoned,
        "token_generated": tokens_gen
    }

def run_parallel_mcq_syllabus_generator(args):
    index, entry, error_count, error_lock = args
    print_and_log('*' * 80)
    print_and_log(f"\nSyllabus NUMBER {index+1} of {total_syllabi} --- | {current_model}")
    print_and_log()
    return syllabus_and_mcq(new_syllabus=entry, syllabus_index=index, error_count=error_count, error_lock=error_lock)

if __name__ == "__main__":
    #from multiprocessing import freeze_support
    #freeze_support()
    print_and_log(f"💥 Model Used: {current_model}")
    print_and_log(f"🧠 Total Syllabi: {total_syllabi}")

    manager = Manager()
    error_count = manager.Value('i', 0)
    error_lock = manager.Lock()

    all_total_tokens = 0
    all_start = time.time()

    parallel_processes = min(parallel_processes_count, cpu_count())
    print_and_log(f"Using {parallel_processes} parallel processes.")

    ######################## PARALLELIZE ########################
    with Pool(processes=parallel_processes) as pool:
        args = [(index, entry, error_count, error_lock) for index, entry in enumerate(subject_entries)]
        results = pool.map(run_parallel_mcq_syllabus_generator, args)
    ######################## END PARALLELIZE #####################

    all_total_tokens = sum(item["token_generated"] for item in results)
    syllabus_counter = len(results) + 1

    all_time_took = time.time() - all_start
    all_token_avg_speed = all_total_tokens / all_time_took

    print("\n📦📦📦📦 FINAL RESULT 📦📦📦📦\n📦📦📦📦📦📦📦📦📦📦📦📦📦📦")
    print(json.dumps(results, indent=3, ensure_ascii=False))
    print("\n📦📦📦📦📦📦📦📦📦📦📦📦📦📦\n📦📦📦📦📦📦📦📦📦📦📦📦📦📦")

    print_and_log('*' * 80)
    print_and_log(f'\nModel: {current_model}\n')
    print_and_log(f"Total Time Taken: {all_time_took:.2f} | Total Tokens Generated: {all_total_tokens} | Avg Total Token Gen Speed: {all_token_avg_speed:.2f} tokens/sec")
    print_and_log(f"Total Syllabi: {syllabus_counter - 1} | Total Success MCQ : {total_success_mcq} | MCQ Attempt per Syllabus: {max_attempts_can}")
    print_and_log(f"Total ERROR: {error_count.value}")