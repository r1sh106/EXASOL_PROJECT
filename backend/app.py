from flask import Flask,request,jsonify
from werkzeug.utils import secure_filename
from text_extract import text_extraction
import os

app = Flask(__name__)


class ResponseObject:
    def __init__(self,message,module=None,params=None):
        self.module = module
        self.message = message
        self.params = params
        self.params = []

    def __repr__(self):
        return self.message

    def json_response(self):
        return jsonify(self.message)

    def check_param(self):
        return "Params checked Succesfully"
    
@app.route('/')
def index():
    response_object = ResponseObject({"Status":"API is working"})
    return response_object.json_response()

@app.route('/order')
def order_reciever():
    if 'image' not in request.files:
        return jsonify({'error':'No image of the order found !!!!'}), 400

    file = request.files['image']
    if file:
        filename = secure_filename(file)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
        file.save(file_path)
        order_items = text_extraction(file_path)
        return jsonify({'Order Summary':order_items})    
    res_obj = ResponseObject({"Flask is working fine":"Order status","Order recieved":"Sucessfully"})
    return res_obj.json_response()

@app.route('/monthly-report')
def generate_monthly_report():
    report = {
        "Orders":{
            "Sample Order 1": {
                "Items":["Item1","Item2","Item3","Item4"],
                "Quantity":[1,2,6,2],
                "Cost":[200,400,120,600]
            },

            "Sample Order 2": {
                            "Items":["Item1","Item2","Item3","Item4"],
                            "Quantity":[1,2,6,2],
                            "Cost":[200,400,120,600]
            },

            "Sample Order 3": {
                            "Items":["Item1","Item2","Item3","Item4"],
                            "Quantity":[1,2,6,2],
                            "Cost":[200,400,120,600]
            },

            "Sample Order 4": {
                            "Items":["Item1","Item2","Item3","Item4"],
                            "Quantity":[1,2,6,2],
                            "Cost":[200,400,120,600]
            }
        },
        "Customers":{
            "Sample Name 1",
            "Sample Name 2",
            "Sample Name 3"
        }
    }

    return jsonify(report)

if __name__ == "__main__":
    app.run(port=8000,debug=True)
