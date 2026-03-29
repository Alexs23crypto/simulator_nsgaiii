# 🏙️ Shelter Optimization Simulator using NSGA-III

This project implements a multi-objective optimization model based on the NSGA-III algorithm to support decision-making in the selection of optimal emergency shelters.

The application is deployed using Streamlit, allowing users to interactively explore different optimization scenarios based on risk, vulnerability, and population criteria.

---

## 🚀 Live Application

👉 [[Open Streamlit App](#)](https://simulatornsgaiii-ss7ubpdbwux5a539khqxyu.streamlit.app/)

---

## 📌 Features

* Multi-objective optimization using NSGA-III
* Interactive simulation with Streamlit
* Visualization of Pareto fronts
* Integration of risk, vulnerability, and population data
* Scalable structure for research and extensions

---

## 📁 Project Structure

```
repo/
│
├── app/
│ ├── simulador.py # Main Streamlit application
│ ├── functions.py # Helper functions
│ ├── data_app/ # Data used by the simulator
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

Clone the repository:

```
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

Install dependencies:

```
pip install -r requirements.txt
```

---

## ▶️ Usage

Run the Streamlit app locally:

```
streamlit run app/simulator.py
```

---

## 📊 Data

The datasets include:

* Shelter locations
* Vulnerability indices
* Risk indicators
* Population distribution

All data used by the app is stored in:

```
data/app_data/
```

---

## 🧠 Methodology

The project uses the NSGA-III (Non-dominated Sorting Genetic Algorithm III) to:

* Maximize distance between shelters
* Maximize coverage of high-risk and high-vulnerability areas
* Optimize population coverage

---

## 📦 Requirements

Main libraries used:

* pandas
* numpy
* streamlit
* matplotlib
* deap

---

## 👩‍💻 Authors

* **Soledad Espezúa**
* **Amy Checcllo**
* **Alexandra Sanjinez**

---

## 📄 License

This project is for academic and research purposes.
