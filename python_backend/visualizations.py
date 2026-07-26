import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Optional

def create_visualization(
    df: pd.DataFrame,
    chart_type: str,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    parameters: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create Plotly visualizations"""
    
    params = parameters or {}
    title = params.get('title', f'{chart_type.title()} Chart')
    color_by = params.get('colorBy')
    z_column = params.get('zColumn')

    aggregation = str(params.get('aggregation') or '').lower().strip() or None
    if aggregation == 'avg':
        aggregation = 'mean'

    def _looks_like_id(col: Optional[str]) -> bool:
        if not col or col not in df.columns:
            return False
        name = col.lower()
        return (name == 'id' or name.endswith('_id') or name.endswith('id')) and df[col].nunique() >= len(df) * 0.95

    try:
        # Pre-aggregate for category charts. Handles "count of rows per category"
        # and "sum/mean of y per x" — and guards against meaningless y axes like
        # ID columns (summing Student_ID per department is never what users want).
        if chart_type in ('bar', 'line', 'pie') and x_column and x_column in df.columns:
            wants_count = (
                aggregation == 'count'
                or (chart_type == 'bar' and not y_column)
                or (chart_type == 'bar' and aggregation is None and _looks_like_id(y_column))
            )
            if wants_count:
                counted = df[x_column].value_counts().head(50).reset_index()
                counted.columns = [x_column, 'Count']
                df = counted
                y_column = 'Count'
            elif aggregation in ('sum', 'mean', 'median', 'min', 'max') and y_column and y_column in df.columns:
                df = df.groupby(x_column, dropna=False)[y_column].agg(aggregation).reset_index()
                df = df.sort_values(y_column, ascending=False).head(50)
        if chart_type == 'histogram':
            if not x_column:
                raise ValueError("x_column required for histogram")
            fig = px.histogram(df, x=x_column, title=title, color=color_by)
        
        elif chart_type == 'scatter':
            if not x_column or not y_column:
                raise ValueError("x_column and y_column required for scatter plot")
            fig = px.scatter(df, x=x_column, y=y_column, title=title, color=color_by,
                           trendline=params.get('trendline'))
        
        elif chart_type == 'line':
            if not x_column or not y_column:
                raise ValueError("x_column and y_column required for line chart")
            fig = px.line(df, x=x_column, y=y_column, title=title, color=color_by)
        
        elif chart_type == 'bar':
            if not x_column or not y_column:
                raise ValueError("x_column and y_column required for bar chart")
            orientation = params.get('orientation', 'v')
            if orientation == 'h':
                fig = px.bar(df, x=y_column, y=x_column, title=title, color=color_by, orientation='h')
            else:
                fig = px.bar(df, x=x_column, y=y_column, title=title, color=color_by)
        
        elif chart_type == 'box':
            if not y_column:
                raise ValueError("y_column required for box plot")
            fig = px.box(df, x=x_column, y=y_column, title=title, color=color_by)
        
        elif chart_type == 'violin':
            if not y_column:
                raise ValueError("y_column required for violin plot")
            fig = px.violin(df, x=x_column, y=y_column, title=title, color=color_by)
        
        elif chart_type == 'heatmap':
            # Correlation heatmap
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            corr_matrix = df[numeric_cols].corr()
            fig = px.imshow(corr_matrix, 
                          text_auto=True,
                          title=title or 'Correlation Heatmap',
                          color_continuous_scale='RdBu_r',
                          aspect='auto')
        
        elif chart_type == 'correlation':
            # Same as heatmap
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            corr_matrix = df[numeric_cols].corr()
            fig = px.imshow(corr_matrix,
                          text_auto=True,
                          title=title or 'Correlation Matrix',
                          color_continuous_scale='RdBu_r',
                          aspect='auto',
                          labels=dict(color="Correlation"))
        
        elif chart_type == 'pie':
            if not x_column:
                raise ValueError("x_column required for pie chart")
            if y_column and y_column in df.columns:
                # pre-aggregated above (or explicit values column)
                fig = px.pie(df.head(10), values=y_column, names=x_column, title=title)
            else:
                value_counts = df[x_column].value_counts().head(10)
                fig = px.pie(values=value_counts.values, names=value_counts.index, title=title)
        
        elif chart_type == 'donut':
            if not x_column:
                raise ValueError("x_column required for donut chart")
            value_counts = df[x_column].value_counts().head(10)
            fig = px.pie(values=value_counts.values, names=value_counts.index, title=title, hole=0.4)
        
        elif chart_type == 'treemap':
            if not x_column:
                raise ValueError("x_column required for treemap")
            value_counts = df[x_column].value_counts().head(20)
            fig = px.treemap(
                names=value_counts.index,
                parents=[''] * len(value_counts),
                values=value_counts.values,
                title=title
            )
        
        elif chart_type == 'sunburst':
            if not x_column:
                raise ValueError("x_column required for sunburst")
            value_counts = df[x_column].value_counts().head(20)
            fig = px.sunburst(
                names=value_counts.index,
                parents=[''] * len(value_counts),
                values=value_counts.values,
                title=title
            )
        
        elif chart_type == '3d_scatter':
            if not x_column or not y_column or not z_column:
                raise ValueError("x_column, y_column, and z_column required for 3D scatter")
            fig = px.scatter_3d(df, x=x_column, y=y_column, z=z_column, title=title, color=color_by)
        
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        # Update layout for better appearance
        fig.update_layout(
            template='plotly_white',
            font=dict(family='Inter, sans-serif'),
            title_x=0.5
        )
        
        # Convert to Plotly JSON format (to_json converts numpy arrays to plain lists)
        fig_json = json.loads(fig.to_json())
        return {
            "data": fig_json['data'],
            "layout": fig_json['layout'],
            "config": {"responsive": True, "displayModeBar": True}
        }
    
    except Exception as e:
        raise ValueError("Failed to create visualization")

def create_distribution_plot(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Create distribution plot for a column"""
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")
    
    if pd.api.types.is_numeric_dtype(df[column]):
        # Histogram with KDE
        fig = px.histogram(df, x=column, marginal='box', title=f'Distribution of {column}')
    else:
        # Bar chart for categorical
        value_counts = df[column].value_counts().head(20)
        fig = px.bar(x=value_counts.index, y=value_counts.values, 
                    title=f'Distribution of {column}',
                    labels={'x': column, 'y': 'Count'})
    
    fig.update_layout(template='plotly_white', font=dict(family='Inter, sans-serif'))
    
    fig_json = json.loads(fig.to_json())
    return {
        "data": fig_json['data'],
        "layout": fig_json['layout'],
        "config": {"responsive": True}
    }
