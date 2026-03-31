# 🏙️ Scenario-adaptive multi-objective optimization for post-earthquake shelter planning in Lima, Peru

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
│   ├── simulador.py # Main Streamlit application
│   ├── functions.py # Helper functions
│   ├── data_app/ # Data used by the simulator
│   │   ├── albergues_muni.xlsx
│   │   ├── pareto_front_desastroso_full.csv
│   │   ├── pareto_front_fuerte_full.csv
│   │   ├── pareto_front_leve_full.csv
│   │   ├── pareto_front_moderado_full.csv
│   │   ├── pareto_front_muy fuerte_full.csv
│   │   ├── shelters_lima.xlsx
│
├── data/
│   ├── geospatial/
│   │   ├── manzanas (blocks)/
│   │   |   ├── manzanas_caracterizadas_lima.zip
│   │   ├── peru_shapes/
│   │   |   ├── per_admbnda_adm3_ign_20200714.CPG
│   │   |   ├── per_admbnda_adm3_ign_20200714.dbf
│   │   |   ├── per_admbnda_adm3_ign_20200714.prj
│   │   |   ├── per_admbnda_adm3_ign_20200714.sbn
│   │   |   ├── per_admbnda_adm3_ign_20200714.sbx
│   │   |   ├── per_admbnda_adm3_ign_20200714.shp
│   │   |   ├── per_admbnda_adm3_ign_20200714.shp.xml
│   │   |   ├── per_admbnda_adm3_ign_20200714.shx
|
├── src/
│   ├── data_processing/
|   |   ├──Potential Shelters Characterization.py
|
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

## 📊 App Data

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

## 🌍 Geospatial Data

This repository includes geospatial data used to generate the cartographic visualizations presented in the study.

Due to file structure requirements, one of the shapefiles are provided in compressed format:

```
data/geospatial/manzanas (blocks)/manzanas_caracterizadas_lima.zip
```

To use the data:

1. Download the .zip file
2. Extract its contents
3. Ensure all shapefile components (.shp, .shx, .dbf, .prj, .cpg) are in the same folder

Additional shapefiles used for spatial analysis and cartographic visualization are available in:

```
data/geospatial/peru_shapes/
```

These files include administrative boundaries and geographic context for the study area.

Coordinate system: WGS84 (EPSG:32718)
Source: Metropolitan Information System (IMP)

---

## 🧪 Data Processing

The data preprocessing and feature engineering steps are available in:

```
src/data_processing/
```

These scripts include data cleaning, transformation, and computation of key indicators such as risk, vulnerability, and population coverage.

---

## 🧠 Methodology

The project uses the NSGA-III (Non-dominated Sorting Genetic Algorithm III) to:

* Maximize inter-shelter spacing.
* Maximize population coverage.
* Maximize safety.

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

* **Soledad Espezúa** (s.espezual@up.edu.pe)
* **Amy Checcllo** (aa.checclloh@alum.up.edu.pe)
* **Alexandra Sanjinez** (ac.sanjinezm@alum.up.edu.pe)

---

## 📄 License

This project is for academic and research purposes.
