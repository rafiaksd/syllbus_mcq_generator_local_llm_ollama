from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = Flask(__name__)

model_name = "microsoft/Phi-3-mini-4k-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

@app.route('/generate', methods=['POST'])
def generate_text():
    try:
        data = request.get_json()
        prompt = data['prompt']
        max_length = data.get('max_length', 150)

        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_length=max_length)
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        return jsonify({'response': generated_text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=1234)
