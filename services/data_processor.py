import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from io import BytesIO
import os


class DataProcessingError(Exception):
    pass


class DataProcessor:
    ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv']
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    @staticmethod
    def validate_file(file_obj) -> Tuple[bool, str]:
        if not file_obj:
            return False, "No se proporcionó ningún archivo"
        
        if hasattr(file_obj, 'size'):
            if file_obj.size == 0:
                return False, "El archivo está vacío"
            if file_obj.size > DataProcessor.MAX_FILE_SIZE:
                return False, f"El archivo excede el tamaño máximo de {DataProcessor.MAX_FILE_SIZE // (1024*1024)}MB"
        
        filename = getattr(file_obj, 'name', '')
        if not filename:
            return False, "El archivo no tiene nombre"
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in DataProcessor.ALLOWED_EXTENSIONS:
            return False, f"Formato no permitido. Use: {', '.join(DataProcessor.ALLOWED_EXTENSIONS)}"
        
        return True, "Archivo válido"
    
    @staticmethod
    def read_file(file_obj) -> pd.DataFrame:
        filename = getattr(file_obj, 'name', '')
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            if ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_obj, engine='openpyxl' if ext == '.xlsx' else None)
            elif ext == '.csv':
                try:
                    df = pd.read_csv(file_obj, encoding='utf-8')
                except UnicodeDecodeError:
                    file_obj.seek(0)
                    df = pd.read_csv(file_obj, encoding='latin-1')
            else:
                raise DataProcessingError(f"Formato no soportado: {ext}")
            
            if df.empty:
                raise DataProcessingError("El archivo no contiene datos")
            
            if len(df.columns) == 0:
                raise DataProcessingError("El archivo no tiene columnas válidas")
            
            return df
        
        except pd.errors.EmptyDataError:
            raise DataProcessingError("El archivo CSV está vacío")
        except pd.errors.ParserError as e:
            raise DataProcessingError(f"Error al parsear el archivo: {str(e)}")
        except Exception as e:
            if isinstance(e, DataProcessingError):
                raise
            raise DataProcessingError(f"Error al leer el archivo: {str(e)}")
    
    @staticmethod
    def get_columns_info(df: pd.DataFrame) -> Dict[str, Any]:
        columns_info = {}
        
        for col in df.columns:
            col_data = df[col]
            non_null = col_data.dropna()
            
            info = {
                'name': str(col),
                'total_rows': len(df),
                'non_null_count': len(non_null),
                'null_count': len(df) - len(non_null),
                'dtype': str(col_data.dtype),
            }
            
            dtype_str = str(col_data.dtype)
            if dtype_str in ('object', 'str') or pd.api.types.is_string_dtype(col_data) or pd.api.types.is_categorical_dtype(col_data):
                unique_values = non_null.unique()
                info['type'] = 'categorical'
                info['unique_count'] = len(unique_values)
                info['unique_values'] = [str(v) for v in unique_values[:20]]
                info['value_counts'] = {str(k): int(v) for k, v in non_null.value_counts().head(10).items()}
            elif pd.api.types.is_numeric_dtype(col_data):
                info['type'] = 'numeric'
                info['min'] = float(non_null.min()) if len(non_null) > 0 else None
                info['max'] = float(non_null.max()) if len(non_null) > 0 else None
                info['mean'] = float(non_null.mean()) if len(non_null) > 0 else None
                info['std'] = float(non_null.std()) if len(non_null) > 0 else None
            else:
                info['type'] = 'other'
            
            columns_info[str(col)] = info
        
        return columns_info
    
    @staticmethod
    def analyze_categorical_column(df: pd.DataFrame, column_name: str, success_category: str) -> Dict[str, Any]:
        if column_name not in df.columns:
            raise DataProcessingError(f"La columna '{column_name}' no existe en el archivo")
        
        col_data = df[column_name].dropna()
        N = len(col_data)
        
        if N == 0:
            raise DataProcessingError("La columna no contiene datos válidos")
        
        value_counts = col_data.value_counts()
        categories = {str(k): int(v) for k, v in value_counts.items()}
        
        K = categories.get(success_category, 0)
        
        if K == 0:
            raise DataProcessingError(f"La categoría '{success_category}' no existe en la columna o tiene 0 ocurrencias")
        
        return {
            'N': N,
            'K': K,
            'p': round(K / N, 6),
            'categories': categories,
            'success_category': success_category,
            'column_name': column_name,
        }
    
    @staticmethod
    def get_preview_data(df: pd.DataFrame, max_rows: int = 100) -> Dict[str, Any]:
        preview_df = df.head(max_rows)
        
        return {
            'columns': [str(col) for col in df.columns],
            'rows': preview_df.values.tolist()[:max_rows],
            'total_rows': len(df),
            'preview_rows': len(preview_df),
            'headers': [str(col) for col in df.columns],
        }
    
    @staticmethod
    def dataframe_to_html_table(df: pd.DataFrame, max_rows: int = 50) -> str:
        preview_df = df.head(max_rows)
        return preview_df.to_html(
            classes='data-table',
            index=False,
            na_rep='-',
            escape=True,
            max_rows=max_rows
        )
