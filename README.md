# 🚨 AI-Powered Early Warning System

A smart disaster alert system that predicts and generates **PDF-based early warnings** for Earthquakes, Floods, and Heatwaves.

This project is built using **Python (Flask)** and a **simple HTML/CSS interface**. It leverages trained ML models to generate location-specific warnings for:

- 🏛️ Government agencies  
- 🧑‍🤝‍🧑 NGOs  
- 👥 Public users  

---

---

## 🚀 How to Run the Project

### 1. Clone the Repository

```bash
git clone https://github.com/ahkhan-nafrok/Early-Warning-Systems.git
cd early-warning-system

```
### 2. Set Up Python Environment
✅ Python 3.7+ required
```
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Flask App
```
python app.py
```
The web interface will be available at:
http://localhost:5000


## 📄 How It Works
1.User opens the index.html page served by Flask.

2.Selects the disaster type and inputs location (optional).

3.The backend loads the relevant trained model (flood, earthquake, heatwave).

4.Predictions are made based on input and dataset.

    A custom warning PDF is generated with:

    Disaster type & severity

    Location-specific notes
 
    Actionable recommendations

    PDF is saved under generated_pdfs/ folder.


## 🔧 Tech Stack
```
Component	Tool/Lib
Backend	Flask (Python)
Frontend	HTML + CSS
ML Models	scikit-learn
PDF Gen	reportlab / fpdf
```

## 📢 Example Use Cases
 * 🛂 Government alerting systems

 * 🚑 NGO disaster coordination

 * 📱 Community safety dashboards

 * 📄 Automatic PDF-based email alerts (can be integrated
