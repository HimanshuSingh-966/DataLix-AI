import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from sklearn.cluster import KMeans, DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go
import plotly.express as px

def perform_ml_analysis(
    df: pd.DataFrame,
    analysis_type: str,
    parameters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Perform ML analysis operations:
    - anomaly_detection
    - clustering
    - dimensionality_reduction
    - feature_importance
    """
    
    params = parameters or {}
    
    if analysis_type == 'anomaly_detection':
        return detect_anomalies(df, params)
    elif analysis_type == 'clustering':
        return perform_clustering(df, params)
    elif analysis_type == 'dimensionality_reduction':
        return reduce_dimensions(df, params)
    elif analysis_type == 'feature_importance':
        return calculate_feature_importance(df, params)
    else:
        raise ValueError(f"Unsupported analysis type: {analysis_type}")

def detect_anomalies(df: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
    """Detect anomalies using Isolation Forest"""
    
    # Select numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return {"error": "No numeric columns found for anomaly detection"}
    
    # Prepare data
    X = df[numeric_cols].fillna(df[numeric_cols].mean())
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Isolation Forest
    contamination = parameters.get('contamination', 0.1)
    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(X_scaled)
    
    # -1 for anomalies, 1 for normal
    anomalies = predictions == -1
    anomaly_count = anomalies.sum()
    
    # Add results to dataframe copy
    df_result = df.copy()
    df_result['anomaly'] = anomalies
    df_result['anomaly_score'] = model.score_samples(X_scaled)
    
    # Create visualization if we have 2+ numeric columns
    visualization = None
    if len(numeric_cols) >= 2:
        fig = px.scatter(
            df_result,
            x=numeric_cols[0],
            y=numeric_cols[1],
            color='anomaly',
            title='Anomaly Detection Results',
            labels={'anomaly': 'Is Anomaly'},
            color_discrete_map={True: 'red', False: 'blue'}
        )
        fig.update_layout(template='plotly_white')
        visualization = {
            "data": fig.to_dict()['data'],
            "layout": fig.to_dict()['layout']
        }
    
    return {
        "analysisType": "anomaly_detection",
        "algorithm": "Isolation Forest",
        "results": {
            "totalRows": len(df),
            "anomaliesDetected": int(anomaly_count),
            "anomalyPercentage": float((anomaly_count / len(df)) * 100),
            "anomalyIndices": df_result[anomalies].index.tolist()
        },
        "visualization": visualization,
        "metrics": {
            "contamination": contamination,
            "featuresUsed": numeric_cols
        }
    }

def perform_clustering(df: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
    """Perform clustering analysis"""
    
    # Select numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return {"error": "No numeric columns found for clustering"}
    
    # Prepare data
    X = df[numeric_cols].fillna(df[numeric_cols].mean())
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    algorithm = parameters.get('algorithm', 'kmeans')
    
    if algorithm == 'kmeans':
        n_clusters = parameters.get('n_clusters', 3)
        model = KMeans(n_clusters=n_clusters, random_state=42)
        labels = model.fit_predict(X_scaled)
        
        metrics = {
            "n_clusters": n_clusters,
            "inertia": float(model.inertia_)
        }
    
    elif algorithm == 'dbscan':
        eps = parameters.get('eps', 0.5)
        min_samples = parameters.get('min_samples', 5)
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(X_scaled)
        
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        
        metrics = {
            "n_clusters": n_clusters,
            "n_noise_points": n_noise,
            "eps": eps,
            "min_samples": min_samples
        }
    
    else:
        raise ValueError(f"Unsupported clustering algorithm: {algorithm}")
    
    # Add cluster labels to dataframe
    df_result = df.copy()
    df_result['cluster'] = labels
    
    # Create visualization
    visualization = None
    if len(numeric_cols) >= 2:
        fig = px.scatter(
            df_result,
            x=numeric_cols[0],
            y=numeric_cols[1],
            color='cluster',
            title=f'{algorithm.upper()} Clustering Results',
            labels={'cluster': 'Cluster'}
        )
        fig.update_layout(template='plotly_white')
        visualization = {
            "data": fig.to_dict()['data'],
            "layout": fig.to_dict()['layout']
        }
    
    # Cluster statistics
    cluster_counts = pd.Series(labels).value_counts().to_dict()
    
    return {
        "analysisType": "clustering",
        "algorithm": algorithm,
        "results": {
            "clusterCounts": {int(k): int(v) for k, v in cluster_counts.items()},
            "totalClusters": len(set(labels)),
            "labels": labels.tolist()
        },
        "visualization": visualization,
        "metrics": metrics
    }

def reduce_dimensions(df: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
    """Perform dimensionality reduction (PCA or t-SNE)"""
    
    # Select numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return {"error": "No numeric columns found for dimensionality reduction"}
    
    # Prepare data
    X = df[numeric_cols].fillna(df[numeric_cols].mean())
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    algorithm = parameters.get('algorithm', 'pca')
    n_components = parameters.get('n_components', 2)
    
    if algorithm == 'pca':
        model = PCA(n_components=n_components)
        X_reduced = model.fit_transform(X_scaled)
        
        explained_variance = model.explained_variance_ratio_.tolist()
        metrics = {
            "explained_variance_ratio": explained_variance,
            "total_explained_variance": float(sum(explained_variance))
        }
    
    elif algorithm == 'tsne':
        perplexity = parameters.get('perplexity', 30)
        model = TSNE(n_components=n_components, perplexity=perplexity, random_state=42)
        X_reduced = model.fit_transform(X_scaled)
        
        metrics = {
            "perplexity": perplexity
        }
    
    else:
        raise ValueError(f"Unsupported dimensionality reduction algorithm: {algorithm}")
    
    # Create visualization
    visualization = None
    if n_components == 2:
        df_viz = pd.DataFrame({
            'Component 1': X_reduced[:, 0],
            'Component 2': X_reduced[:, 1]
        })
        
        fig = px.scatter(
            df_viz,
            x='Component 1',
            y='Component 2',
            title=f'{algorithm.upper()} - 2D Projection',
            opacity=0.7
        )
        fig.update_layout(template='plotly_white')
        visualization = {
            "data": fig.to_dict()['data'],
            "layout": fig.to_dict()['layout']
        }
    
    return {
        "analysisType": "dimensionality_reduction",
        "algorithm": algorithm,
        "results": {
            "n_components": n_components,
            "original_dimensions": len(numeric_cols),
            "reduced_data": X_reduced.tolist()
        },
        "visualization": visualization,
        "metrics": metrics
    }

def calculate_feature_importance(df: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
    """Calculate feature importance using correlation with target"""
    
    target_column = parameters.get('target_column')
    if not target_column or target_column not in df.columns:
        return {"error": "Valid target_column required for feature importance"}
    
    # Select numeric columns (excluding target)
    numeric_cols = [col for col in df.select_dtypes(include=[np.number]).columns if col != target_column]
    
    if not numeric_cols:
        return {"error": "No numeric feature columns found"}
    
    # Calculate correlation with target
    correlations = df[numeric_cols + [target_column]].corr()[target_column].drop(target_column)
    
    # Sort by absolute correlation
    importance = correlations.abs().sort_values(ascending=False)
    
    # Create visualization
    fig = px.bar(
        x=importance.values,
        y=importance.index,
        orientation='h',
        title='Feature Importance (Correlation with Target)',
        labels={'x': 'Absolute Correlation', 'y': 'Feature'}
    )
    fig.update_layout(template='plotly_white', yaxis={'categoryorder': 'total ascending'})
    
    visualization = {
        "data": fig.to_dict()['data'],
        "layout": fig.to_dict()['layout']
    }
    
    return {
        "analysisType": "feature_importance",
        "algorithm": "Correlation Analysis",
        "results": {
            "importance_scores": importance.to_dict(),
            "top_features": importance.head(10).index.tolist()
        },
        "visualization": visualization,
        "metrics": {
            "target_column": target_column,
            "n_features": len(numeric_cols)
        }
    }
