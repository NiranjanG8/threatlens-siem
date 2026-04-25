# 🔐 ThreatLens           - An Intelligent Security Monitoring & Detection Engine

<p align="center">
  <img src="threatlens.png" width="700" height="700"/>
</p>


---

## 🚀 Overview

**ThreatLens** is a mini **SIEM (Security Information and Event Management)** system designed to simulate real-world security monitoring.

It ingests logs, normalizes them, detects threats using **rule-based logic and machine learning**, and visualizes alerts via a dashboard.

Inspired by enterprise tools like Splunk and Elastic Stack.

---

## 🧩 Features

* 🔍 Log Parsing & Normalization
* ⚡ Real-time Log Monitoring (Watchdog)
* 🛡️ Rule-based Detection

  * Brute Force Attacks
  * Suspicious Activity
* 🤖 ML-based Anomaly Detection (Isolation Forest)
* 🌐 REST API using Flask
* 📊 Dashboard using Streamlit
* 🐳 Dockerized Deployment

---

## 🏗️ Architecture

Logs → Parser → Normalizer → Detection Engine → ML Model → Alerts → API → Dashboard

---

## 🚨 Detection Capabilities

* 🔐 Brute Force Attack Detection
* 📡 Suspicious IP Activity
* 📈 High Request Frequency Detection
* 🤖 Anomaly Detection using Machine Learning

---

## 📸 Dashboard Preview

<p align="center">
  <img src="dashboard.png" width="700"/>
</p>

---

## ⚙️ Tech Stack

* Python
* Flask
* Streamlit
* Scikit-learn
* NumPy
* Docker

---

## 📁 Project Structure

```
threatlens-siem
│
├── data/
├── src/
├── dashboard/
├── reports/
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## ▶️ Getting Started

### 1️⃣ Clone the Repository

```
git clone https://github.com/your-username/threatlens-siem.git
cd threatlens-siem
```

---

### 2️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

### 3️⃣ Run Detection Engine

```
python src/main.py
```

ThreatLens now loads sources from `data/log_sources.json`, so you can combine:

* file-based logs
* Windows Event Logs (`Security`, `Application`, `System`)

Edit that config file to enable or disable sources and tune `max_events`.

---

### 4️⃣ Run API

```
python src/api.py
```

Useful endpoints:

* `/health` → service status
* `/analyze` → generated alerts
* `/events` → normalized ingested events

---

### 5️⃣ Run Dashboard

```
streamlit run dashboard/app.py
```

### 6️⃣ Start API + Dashboard Together

```
powershell -ExecutionPolicy Bypass -File .\start-threatlens.ps1
```

This starts both services in the background, writes logs to `logs/`, and prints the local API and dashboard URLs.
It runs the Streamlit dashboard in headless mode, so your browser will not be opened automatically.

---

## 🐳 Run with Docker

```
docker build -t threatlens .
docker run -p 5000:5000 threatlens
```

---

## 🧪 Attack Simulation (Optional)

You can simulate real attacks to test detection:

* Brute Force → Hydra
* Port Scan → Nmap
* Traffic Flood → Curl

---

## 📌 Why This Project Matters

ThreatLens demonstrates real-world **Security Operations Center (SOC)** concepts:

* Log analysis
* Threat detection
* Detection engineering
* Security automation

This project is ideal for roles like:

* Security Analyst
* SOC Analyst
* Security Engineer

---

## 📈 Future Improvements

ThreatLens is just getting started, and there are several areas planned for expansion to make it more reflective of real-world SOC and SIEM operations:

* Add support for more log sources such as Linux authentication logs, syslog, Apache/Nginx logs, and `journalctl`
* Expand Windows Event Log detection coverage for important Event IDs such as `4624`, `4625`, `4688`, `4698`, and `7045`
* Introduce new detections for brute force activity, lateral movement, persistence, log clearing, and possible data exfiltration
* Build SIEM-style alert triage workflows with status tracking, assignment, notes, and investigation history
* Map detections to **MITRE ATT&CK** tactics and techniques for stronger security context
* Preserve raw log evidence alongside normalized events for better incident investigation
* Add event correlation across multiple sources, users, hosts, and timestamps
* Improve the dashboard with deeper drilldowns, investigation views, and alert status widgets
* Add threat intelligence enrichment for suspicious IPs and domains
* Introduce stronger anomaly detection models beyond simple IP activity analysis
* Store alerts and events in a database for better historical search and reporting
* Add real-time notifications through Slack, email, or webhooks

---

## 👨‍💻 Author

**Niranjan G**

---

## 📜 License

This project is licensed under the MIT License.
