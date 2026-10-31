# Smart-Traffic-Congestion-Predictor-and-Navigator
Smart Traffic Congestion Predictor and Navigator using Random Forest, A* routing, and OpenStreetMap for Bengaluru, India.
# Smart Traffic Congestion Predictor and Navigator

An intelligent full-stack web application that predicts traffic congestion and recommends optimized driving routes across **Bengaluru, India**, using Machine Learning, Graph Theory, and real-world road network data.

The system combines a **Random Forest congestion prediction model** with **A\* shortest-path routing** to identify alternative routes that balance travel time and traffic congestion.

## Features

- **Interactive Route Planner:** Select source and destination using an interactive OpenStreetMap interface.
- **Traffic Congestion Prediction:** Classify road congestion into Low, Medium, and Hard (High).
- **Congestion-Aware Navigation:** Calculate routes using travel-time costs and congestion penalties.
- **Multiple Route Alternatives:** Generate up to three alternative driving routes.
- **Route Visualization:** Display color-coded routes on an interactive map.
- **Route Analytics:** View distance, estimated travel time, and congestion distribution.
- **Model Performance Dashboard:** Explore accuracy, macro F1-score, confusion matrix, and classification metrics.
- **Traffic Analytics:** Analyze traffic trends, peak-hour congestion, and environmental impacts.

## Machine Learning

**Algorithm:** Random Forest Classifier

**Dataset:** Bangalore Traffic Pulse dataset

**Dataset size:** 8,936 observation records

**Prediction classes:**
- Low
- Medium
- Hard (High)

### Model Evaluation

| Metric | Result |
|---|---|
| Test Accuracy | 90.16% |
| Macro F1 Score | 0.87 |

### Input Features

- Vehicle volume
- Average speed
- Travel Time Index (TTI)
- Road capacity utilization
- Incident reports
- Day of the week
- Month
- Weather conditions
- Roadwork presence

The model predicts congestion levels for road segments, which are subsequently used by the routing engine.

## Routing Algorithm

The application uses a real-world Bengaluru road network obtained from OpenStreetMap and processed using OSMnx and NetworkX.

### Road Network

- Nodes: 13,863
- Directed edges: 35,464

The road network is stored locally in GraphML format.

### A* Search

The routing engine uses A* shortest-path search with a congestion-weighted travel cost.

**Cost function:**

Cost(e) = TravelTime(e) × (1 + CongestionPenalty(e))

Road segments with higher congestion receive increased routing costs, encouraging the algorithm to consider alternative corridors.

### Route Alternatives

1. **Route 1 – Fastest Route:** Optimizes travel time.
2. **Route 2 – Congestion-Aware Route:** Penalizes congested road segments.
3. **Route 3 – Alternative Route:** Diversifies the route by penalizing previously selected edges.

Each route includes distance, estimated travel time, congestion distribution, and a dominant congestion classification.

## Technology Stack

### Frontend
- React 18
- Vite
- Tailwind CSS
- React-Leaflet
- OpenStreetMap
- Recharts
- Axios
- Lucide Icons

### Backend
- Python 3.13
- FastAPI
- Uvicorn
- Pydantic v2

### Machine Learning
- Scikit-learn
- Pandas
- NumPy
- Joblib

### Routing and GIS
- OSMnx
- NetworkX
- Shapely


## Application Pages

### Route Planner
Interactive Bengaluru map for selecting locations and comparing alternative routes.

### Model Performance
Displays model evaluation metrics, confusion matrix, classification reports, and feature importance.

### Traffic Analytics
Visualizes traffic volume, congestion patterns, peak-hour traffic, and weather-related trends.


## Project Objective

To develop an intelligent traffic navigation system that combines machine learning-based congestion prediction with graph-based route optimization, helping users identify alternative driving routes and make informed navigation decisions.

