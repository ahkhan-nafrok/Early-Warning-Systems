from flask import Flask, render_template, request, send_file
import numpy as np
import tensorflow as tf
import joblib
import json
import os
import datetime
import requests
import tempfile
from fpdf import FPDF

app = Flask(__name__)

# Load models and scalers

heat_model = tf.keras.models.load_model('models/heatwave_prediction_model.h5')
earthquake_model = tf.keras.models.load_model('models/earthquake_prediction_model.h5')
flood_model = tf.keras.models.load_model('models/flood_prediction_model.h5')
flood_scaler = joblib.load('models/flood_scaler.pkl')
heat_scaler = joblib.load('models/heat_scaler.pkl')
earthquake_scaler = joblib.load('models/earthquake_scaler.pkl')

# Load city coordinates and helplines
with open('data/city_coordinates.json') as f:
    CITY_COORDINATES = json.load(f)
    
with open('data/emergency_helplines.json') as f:
    EMERGENCY_HELPLINES = json.load(f)

# Google Maps API Key - Replace with your actual key
GMAPS_API_KEY = "AIzaSyDeuGhbyL2Atc_nKo8ZYhx8LwWL0QYlIOo"

# Alert generation function with earthquake support
def generate_alert(disaster_type, severity, location):
    """Generate customized alerts for different stakeholders with location"""
    alerts = {
        # Government agencies
        'government': {
            'flood': {
                'high': f"URGENT: Severe flooding predicted in {location}. Immediate evacuation needed. Deploy emergency response teams and resources. [City: {location}]",
                'medium': f"WARNING: Moderate flooding expected in {location}. Prepare emergency shelters and response teams. [City: {location}]",
                'low': f"ADVISORY: Minor flooding possible in {location}. Monitor situation and prepare response resources. [City: {location}]"
            },
            'heatwave': {
                'high': f"URGENT: Extreme heat wave predicted in {location}. Activate cooling centers and emergency medical services. [City: {location}]",
                'medium': f"WARNING: Significant heat wave expected in {location}. Prepare public cooling facilities and check on vulnerable populations. [City: {location}]",
                'low': f"ADVISORY: Mild heat wave possible in {location}. Prepare for increased cooling needs and public advisories. [City: {location}]"
            },
            'earthquake': {
                'high': f"URGENT: High earthquake risk detected in {location}. Activate emergency response protocols. Deploy search and rescue teams. [City: {location}]",
                'medium': f"WARNING: Moderate earthquake risk in {location}. Prepare emergency response teams and check building safety protocols. [City: {location}]",
                'low': f"ADVISORY: Low earthquake risk detected in {location}. Review emergency protocols and building safety measures. [City: {location}]"
            }
        },

        # NGOs
        'ngo': {
            'flood': {
                'high': f"Urgent assistance needed: Severe flooding predicted in {location}. Prepare relief supplies, medical teams, and temporary shelters. [City: {location}]",
                'medium': f"Alert: Moderate flooding expected in {location}. Ready relief supplies and volunteer teams. [City: {location}]",
                'low': f"Notice: Minor flooding possible in {location}. Monitor situation and be prepared to assist if needed. [City: {location}]"
            },
            'heatwave': {
                'high': f"Urgent assistance needed: Extreme heat wave predicted in {location}. Prepare water distribution, cooling stations, and medical aid. [City: {location}]",
                'medium': f"Alert: Significant heat wave expected in {location}. Prepare water supplies and check on elderly and vulnerable populations. [City: {location}]",
                'low': f"Notice: Mild heat wave possible in {location}. Consider preparing heat relief measures. [City: {location}]"
            },
            'earthquake': {
                'high': f"Urgent assistance needed: High earthquake risk in {location}. Prepare emergency medical supplies, search and rescue equipment, and temporary shelters. [City: {location}]",
                'medium': f"Alert: Moderate earthquake risk in {location}. Ready emergency supplies and volunteer response teams. [City: {location}]",
                'low': f"Notice: Low earthquake risk in {location}. Review emergency preparedness and supply readiness. [City: {location}]"
            }
        },

        # Public
        'public': {
            'flood': {
                'high': f"EMERGENCY ALERT: Severe flooding expected in {location}. Evacuate immediately to higher ground. Follow official instructions. [City: {location}]",
                'medium': f"FLOOD WARNING: Significant flooding possible in {location}. Prepare emergency supplies and be ready to evacuate if instructed. [City: {location}]",
                'low': f"FLOOD WATCH: Minor flooding possible in {location}. Stay informed and prepare emergency supplies. [City: {location}]"
            },
            'heatwave': {
                'high': f"EMERGENCY ALERT: Dangerous heat wave expected in {location}. Stay indoors, drink plenty of water, and seek cool environments. [City: {location}]",
                'medium': f"HEAT WARNING: High temperatures expected in {location}. Limit outdoor activities, stay hydrated, and check on vulnerable neighbors. [City: {location}]",
                'low': f"HEAT ADVISORY: Warm temperatures expected in {location}. Stay hydrated and take breaks from the heat. [City: {location}]"
            },
            'earthquake': {
                'high': f"EMERGENCY ALERT: High earthquake risk in {location}. Secure heavy objects, identify safe spots, and be ready to Drop, Cover, and Hold On. [City: {location}]",
                'medium': f"EARTHQUAKE WARNING: Moderate seismic activity possible in {location}. Review earthquake safety plans and secure loose items. [City: {location}]",
                'low': f"EARTHQUAKE ADVISORY: Low seismic risk detected in {location}. Review earthquake preparedness and safety procedures. [City: {location}]"
            }
        }
    }

    return {
        'government': alerts['government'][disaster_type][severity],
        'ngo': alerts['ngo'][disaster_type][severity],
        'public': alerts['public'][disaster_type][severity]
    }

# PDF generation class
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "DISASTER MANAGEMENT AUTHORITY", ln=True, align="C")
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, f"OFFICIAL {self.disaster_type.upper()} {self.severity.upper()} ALERT", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, "This is an automatically generated alert from the Disaster Early Warning System.", ln=True, align="C")

# PDF generation function with earthquake support
def generate_alert_pdf(disaster_type, severity, location, data):
    try:
        # Create directory if it doesn't exist
        os.makedirs('generated_pdfs', exist_ok=True)
        
        pdf = PDF()
        pdf.disaster_type = disaster_type
        pdf.severity = severity
        pdf.add_page()

        # Map Configuration
        try:
            lat, lon = CITY_COORDINATES[location]
            map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=12&size=600x300&maptype=roadmap&markers=color:red%7C{lat},{lon}&key=AIzaSyDeuGhbyL2Atc_nKo8ZYhx8LwWL0QYlIOo"
            response = requests.get(map_url)

            if response.status_code == 200:
                # Save image to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
                    tmpfile.write(response.content)
                    img_path = tmpfile.name

                # Add image to PDF and cleanup
                pdf.image(img_path, x=10, y=40, w=180)
                os.unlink(img_path)
                pdf.ln(120)
            else:
                pdf.cell(0, 10, f"Map unavailable (Status: {response.status_code})", ln=True)
        except KeyError:
            pdf.cell(0, 10, f"Coordinates not found for {location}", ln=True)
        except Exception as map_error:
            pdf.cell(0, 10, f"Map error: {str(map_error)}", ln=True)

        # Rest of PDF content
        pdf.set_font("Arial", "", 10)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 10, f"Issued on: {current_time}", ln=True)

        # Alert Details
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"LOCATION: {location}", ln=True)
        pdf.cell(0, 10, "ALERT DETAILS:", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # Data display
        pdf.set_font("Arial", "", 12)
        if disaster_type.lower() == 'flood':
            pdf.cell(0, 10, f"Rainfall: {data['rainfall']:.1f} mm", ln=True)
            pdf.cell(0, 10, f"River Level: {data['river_level']:.1f} m", ln=True)
            pdf.cell(0, 10, f"Soil Moisture: {data['soil_moisture']:.1f}%", ln=True)
        elif disaster_type.lower() == 'heatwave':
            pdf.cell(0, 10, f"Maximum Temperature: {data['max_temp']:.1f}°C", ln=True)
            pdf.cell(0, 10, f"Humidity: {data['humidity']:.1f}%", ln=True)
            pdf.cell(0, 10, f"Consecutive Hot Days: {data['consecutive_hot_days']}", ln=True)
        elif disaster_type.lower() == 'earthquake':
            pdf.cell(0, 10, f"Seismic Activity: {data['seismic_activity']:.2f}", ln=True)
            pdf.cell(0, 10, f"Ground Displacement: {data['ground_displacement']:.2f} mm", ln=True)
            pdf.cell(0, 10, f"Fault Distance: {data['fault_distance']:.1f} km", ln=True)
            pdf.cell(0, 10, f"Previous Earthquakes (30 days): {data['previous_earthquakes']}", ln=True)
            if 'magnitude' in data:
                pdf.cell(0, 10, f"Predicted Magnitude: {data['magnitude']:.1f}", ln=True)

        # Alert messages
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "ALERT MESSAGE:", ln=True)

        alerts = generate_alert(disaster_type.lower(), severity.lower(), location)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, f"For Government Agencies:\n{alerts['government']}")
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"For NGOs and Relief Organizations:\n{alerts['ngo']}")
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"For Public Distribution:\n{alerts['public']}")

        # Emergency contacts
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "EMERGENCY HELPLINES:", ln=True)
        pdf.set_font("Arial", "", 12)
        for name, number in EMERGENCY_HELPLINES.items():
            pdf.cell(0, 10, f"{name}: {number}", ln=True)

        # Safety instructions
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "SAFETY INSTRUCTIONS:", ln=True)
        safety_tips = {
            "flood": [
                "Move to higher ground immediately if instructed to evacuate",
                "Turn off electricity and gas if possible",
                "Avoid walking or driving through flood waters",
                "Follow news channels and official social media for updates",
                "Keep emergency supplies ready (food, water, medicines, documents)"
            ],
            "heatwave": [
                "Stay indoors in air-conditioned environments when possible",
                "Drink plenty of water, even if not thirsty",
                "Wear lightweight, light-colored, loose-fitting clothing",
                "Take cool showers or baths",
                "Check on elderly, sick, and those who live alone"
            ],
            "earthquake": [
                "Drop, Cover, and Hold On during shaking",
                "Stay away from windows, mirrors, and heavy objects",
                "If outdoors, move away from buildings, trees, and power lines",
                "After shaking stops, check for injuries and hazards",
                "Be prepared for aftershocks",
                "Have emergency supplies ready (water, food, flashlight, radio)"
            ]
        }
        pdf.set_font("Arial", "", 12)
        for tip in safety_tips.get(disaster_type.lower(), []):
            pdf.cell(0, 10, f"- {tip}", ln=True)

        # Save PDF
        filename = f"generated_pdfs/{disaster_type.lower()}_{severity.lower()}_{location.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(filename, "F")

        return filename
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return None

# Homepage with form
@app.route('/')
def home():
    return render_template('index.html', cities=list(CITY_COORDINATES.keys()))

# Prediction endpoint with earthquake support
@app.route('/predict', methods=['POST'])
def predict():
    # Get form data
    disaster_type = request.form['disaster']
    city = request.form['city']
    generate_pdf = 'pdf' in request.form
    pdf_path = None
    alerts = None
    severity = None
    
    if disaster_type == 'flood':
        # Get flood parameters
        rainfall = float(request.form.get('rainfall', 100.0))
        river_level = float(request.form.get('river_level', 5.0))
        soil_moisture = float(request.form.get('soil_moisture', 50.0))
        
        # Prepare input
        input_data = np.array([[rainfall, river_level, soil_moisture]])
        scaled_input = flood_scaler.transform(input_data)
        
        # Predict
        prediction = flood_model.predict(scaled_input)[0][0]
        
        # Determine severity
        if prediction > 0.8:
            severity = 'high'
        elif prediction > 0.5:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Only show alerts if significant risk
        if prediction > 0.3:
            risk_detected = True
            alerts = generate_alert('flood', severity, city)
            
            # Generate PDF if requested
            if generate_pdf:
                data = {
                    'rainfall': rainfall,
                    'river_level': river_level,
                    'soil_moisture': soil_moisture
                }
                pdf_path = generate_alert_pdf('flood', severity, city, data)
        else:
            risk_detected = False
        
        return render_template('result.html', 
                              risk_detected=risk_detected,
                              prediction=prediction,
                              alerts=alerts,
                              severity=severity,
                              disaster_type='Flood',
                              pdf_path=pdf_path,
                              city=city,
                              input_data={
                                  'rainfall': rainfall,
                                  'river_level': river_level,
                                  'soil_moisture': soil_moisture
                              })
    
    elif disaster_type == 'heatwave':
        # Get heatwave parameters
        max_temp = float(request.form.get('max_temp', 35.0))
        humidity = float(request.form.get('humidity', 50.0))
        hot_days = int(request.form.get('hot_days', 3))
        
        # Prepare input
        input_data = np.array([[max_temp, humidity, hot_days]])
        scaled_input = heat_scaler.transform(input_data)
        
        # Predict
        prediction = heat_model.predict(scaled_input)[0][0]
        
        # Determine severity
        if prediction > 0.8:
            severity = 'high'
        elif prediction > 0.5:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Only show alerts if significant risk
        if prediction > 0.3:
            risk_detected = True
            alerts = generate_alert('heatwave', severity, city)
            
            # Generate PDF if requested
            if generate_pdf:
                data = {
                    'max_temp': max_temp,
                    'humidity': humidity,
                    'consecutive_hot_days': hot_days
                }
                pdf_path = generate_alert_pdf('heatwave', severity, city, data)
        else:
            risk_detected = False
        
        return render_template('result.html', 
                              risk_detected=risk_detected,
                              prediction=prediction,
                              alerts=alerts,
                              severity=severity,
                              disaster_type='Heat Wave',
                              pdf_path=pdf_path,
                              city=city,
                              input_data={
                                  'max_temp': max_temp,
                                  'humidity': humidity,
                                  'hot_days': hot_days
                              })
    
    elif disaster_type == 'earthquake':
        # Get earthquake parameters
        seismic_activity = float(request.form.get('seismic_activity', 2.5))
        ground_displacement = float(request.form.get('ground_displacement', 0.5))
        fault_distance = float(request.form.get('fault_distance', 10.0))
        previous_earthquakes = int(request.form.get('previous_earthquakes', 2))
        
        # Prepare input
        input_data = np.array([[seismic_activity, ground_displacement, fault_distance, previous_earthquakes]])
        scaled_input = earthquake_scaler.transform(input_data)
        
        # Predict
        prediction = earthquake_model.predict(scaled_input)[0][0]
        
        # Determine severity and estimated magnitude
        if prediction > 0.8:
            severity = 'high'
            estimated_magnitude = 6.0 + (prediction - 0.8) * 10  # Scale to magnitude
        elif prediction > 0.5:
            severity = 'medium'
            estimated_magnitude = 4.5 + (prediction - 0.5) * 5
        else:
            severity = 'low'
            estimated_magnitude = 3.0 + prediction * 3
        
        # Only show alerts if significant risk
        if prediction > 0.3:
            risk_detected = True
            alerts = generate_alert('earthquake', severity, city)
            
            # Generate PDF if requested
            if generate_pdf:
                data = {
                    'seismic_activity': seismic_activity,
                    'ground_displacement': ground_displacement,
                    'fault_distance': fault_distance,
                    'previous_earthquakes': previous_earthquakes,
                    'magnitude': estimated_magnitude
                }
                pdf_path = generate_alert_pdf('earthquake', severity, city, data)
        else:
            risk_detected = False
        
        return render_template('result.html', 
                              risk_detected=risk_detected,
                              prediction=prediction,
                              alerts=alerts,
                              severity=severity,
                              disaster_type='Earthquake',
                              pdf_path=pdf_path,
                              city=city,
                              input_data={
                                  'seismic_activity': seismic_activity,
                                  'ground_displacement': ground_displacement,
                                  'fault_distance': fault_distance,
                                  'previous_earthquakes': previous_earthquakes,
                                  'estimated_magnitude': f"{estimated_magnitude:.1f}"
                              })
    
    return "Invalid disaster type", 400

# PDF download endpoint
@app.route('/download/<path:filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    # Create required directories
    os.makedirs('models', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('generated_pdfs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True)