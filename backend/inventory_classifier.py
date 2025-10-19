from google import genai
import json

client = genai.Client()

data_example = "{'data': {'category (example: food)': {'item' : 'quantity', 'item': 'quantity',}, {'category (example: clothes)' : {'item' : 'quantity', 'item' : 'quantity'}}}}"

text = "I have 5 boxes of apples, 10 pizzas and 5 kilograms of rice. I also have 5 jeans and 200 hoodies. I also have 4 bags of chips. I have 5 laptops and 2 monitors as well as a spare phone. I have 5 more laptops."
# prompt = "Process the text into a json file format with the data being in the form 'item': 'quantity', (in the quantity field, include the unit(NOT THE FOOD ITSELF)) (if there is no specific unit, just add 'units') and so on for the following data: " + text + "Give me only the json with no additional text."

prompt = "Process the text into a json file format with the data being in the form " + data_example + " . You decide the categories. (in the quantity field, include the unit(NOT THE FOOD ITSELF)) (if there is no specific unit, just add 'units') and so on for the following data: " + text + "Give me only the json with no additional text."

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

json_data = json.loads(response.text.replace('json', '').replace('```', ''))


organization = "Food Distr."

with open('inventory.csv', 'w') as f:
    f.write('organization')
    f.write('|')
    f.write('categories')
    f.write('|')
    f.write('items\n')

with open('inventory.csv', 'a') as f:
    f.write(organization)
    f.write('|')
    f.write(str(list(json_data['data'].keys())))
    f.write('|')
    f.write(str(json_data['data']))
