"""
Monitoring and Analytics Module for B2B AI E-commerce Content Generator

This module provides monitoring capabilities, performance analytics,
and system health checks for the application.
"""

import streamlit as st
import pandas as pd
import time
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    operation: str
    duration: float
    success: bool
    timestamp: datetime
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """System health status data structure."""
    services_initialized: bool
    config_valid: bool
    api_connection: bool
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    last_check: Optional[datetime] = None


class ApplicationMonitor:
    """Application monitoring and analytics manager."""
    
    def __init__(self):
        """Initialize application monitor."""
        self.logger = logging.getLogger(__name__)
        self.metrics_history: List[PerformanceMetric] = []
        self.max_history_size = 1000
        
    def record_metric(
        self,
        operation: str,
        duration: float,
        success: bool,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a performance metric.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            success: Whether the operation was successful
            additional_data: Additional metric data
        """
        metric = PerformanceMetric(
            operation=operation,
            duration=duration,
            success=success,
            timestamp=datetime.now(),
            additional_data=additional_data or {}
        )
        
        self.metrics_history.append(metric)
        
        # Limit history size
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        # Update session state metrics
        if 'app_metrics' in st.session_state:
            if success:
                st.session_state.app_metrics['requests_processed'] += 1
            else:
                st.session_state.app_metrics['errors_encountered'] += 1
            
            st.session_state.app_metrics['last_activity'] = pd.Timestamp.now()
    
    def get_system_health(self) -> SystemHealth:
        """
        Get current system health status.
        
        Returns:
            SystemHealth object with current status
        """
        try:
            # Check if services are initialized
            services_initialized = 'app_services' in st.session_state
            
            # Check configuration validity
            config_valid = False
            api_connection = False
            
            if services_initialized:
                services = st.session_state.app_services
                config_manager = services.get('config_manager')
                llm_service = services.get('llm_service')
                
                if config_manager:
                    validation_result = config_manager.validate_configuration()
                    config_valid = validation_result.is_valid
                
                if llm_service:
                    try:
                        api_connection = llm_service.test_connection()
                    except Exception:
                        api_connection = False
            
            # Get system resource usage
            memory_usage = self._get_memory_usage()
            disk_usage = self._get_disk_usage()
            
            return SystemHealth(
                services_initialized=services_initialized,
                config_valid=config_valid,
                api_connection=api_connection,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                last_check=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return SystemHealth(
                services_initialized=False,
                config_valid=False,
                api_connection=False,
                last_check=datetime.now()
            )
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage percentage."""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return None
        except Exception as e:
            self.logger.warning(f"Could not get memory usage: {e}")
            return None
    
    def _get_disk_usage(self) -> Optional[float]:
        """Get current disk usage percentage."""
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            return None
        except Exception as e:
            self.logger.warning(f"Could not get disk usage: {e}")
            return None
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for the last N hours.
        
        Args:
            hours: Number of hours to include in summary
            
        Returns:
            Dictionary with performance summary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'operations_by_type': {},
                'error_rate': 0.0
            }
        
        total_ops = len(recent_metrics)
        successful_ops = sum(1 for m in recent_metrics if m.success)
        failed_ops = total_ops - successful_ops
        
        # Calculate averages
        avg_duration = sum(m.duration for m in recent_metrics) / total_ops
        success_rate = (successful_ops / total_ops) * 100
        error_rate = (failed_ops / total_ops) * 100
        
        # Group by operation type
        ops_by_type = {}
        for metric in recent_metrics:
            if metric.operation not in ops_by_type:
                ops_by_type[metric.operation] = {
                    'count': 0,
                    'success_count': 0,
                    'total_duration': 0.0
                }
            
            ops_by_type[metric.operation]['count'] += 1
            ops_by_type[metric.operation]['total_duration'] += metric.duration
            if metric.success:
                ops_by_type[metric.operation]['success_count'] += 1
        
        # Calculate averages for each operation type
        for op_type, data in ops_by_type.items():
            data['avg_duration'] = data['total_duration'] / data['count']
            data['success_rate'] = (data['success_count'] / data['count']) * 100
        
        return {
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'failed_operations': failed_ops,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'average_duration': avg_duration,
            'operations_by_type': ops_by_type,
            'time_period_hours': hours
        }
    
    def render_monitoring_dashboard(self) -> None:
        """Render the monitoring dashboard in Streamlit."""
        st.header("📊 Application Monitoring Dashboard")
        
        # System Health Section
        st.subheader("🏥 System Health")
        health = self.get_system_health()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_icon = "✅" if health.services_initialized else "❌"
            st.metric("Services", f"{status_icon} {'Online' if health.services_initialized else 'Offline'}")
        
        with col2:
            config_icon = "✅" if health.config_valid else "❌"
            st.metric("Configuration", f"{config_icon} {'Valid' if health.config_valid else 'Invalid'}")
        
        with col3:
            api_icon = "✅" if health.api_connection else "❌"
            st.metric("API Connection", f"{api_icon} {'Connected' if health.api_connection else 'Disconnected'}")
        
        with col4:
            if health.memory_usage is not None:
                memory_color = "🟢" if health.memory_usage < 80 else "🟡" if health.memory_usage < 90 else "🔴"
                st.metric("Memory Usage", f"{memory_color} {health.memory_usage:.1f}%")
            else:
                st.metric("Memory Usage", "N/A")
        
        # Performance Metrics Section
        st.subheader("⚡ Performance Metrics")
        
        # Time period selector
        time_period = st.selectbox(
            "Time Period",
            options=[1, 6, 24, 168],  # 1h, 6h, 24h, 1week
            format_func=lambda x: f"Last {x} hour{'s' if x > 1 else ''}" if x < 168 else "Last week",
            index=2  # Default to 24 hours
        )
        
        perf_summary = self.get_performance_summary(time_period)
        
        # Performance overview
        perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
        
        with perf_col1:
            st.metric("Total Operations", perf_summary['total_operations'])
        
        with perf_col2:
            st.metric(
                "Success Rate", 
                f"{perf_summary['success_rate']:.1f}%",
                delta=f"{perf_summary['successful_operations']} successful"
            )
        
        with perf_col3:
            st.metric(
                "Error Rate",
                f"{perf_summary['error_rate']:.1f}%",
                delta=f"{perf_summary['failed_operations']} failed"
            )
        
        with perf_col4:
            st.metric(
                "Avg Duration",
                f"{perf_summary['average_duration']:.2f}s"
            )
        
        # Operations breakdown
        if perf_summary['operations_by_type']:
            st.subheader("🔍 Operations Breakdown")
            
            ops_data = []
            for op_type, data in perf_summary['operations_by_type'].items():
                ops_data.append({
                    'Operation': op_type,
                    'Count': data['count'],
                    'Success Rate': f"{data['success_rate']:.1f}%",
                    'Avg Duration': f"{data['avg_duration']:.2f}s",
                    'Total Duration': f"{data['total_duration']:.2f}s"
                })
            
            ops_df = pd.DataFrame(ops_data)
            st.dataframe(ops_df, use_container_width=True)
        
        # Session Metrics
        if 'app_metrics' in st.session_state:
            st.subheader("📱 Session Metrics")
            session_metrics = st.session_state.app_metrics
            
            session_col1, session_col2, session_col3 = st.columns(3)
            
            with session_col1:
                if session_metrics.get('startup_time'):
                    uptime = time.time() - session_metrics['startup_time']
                    uptime_str = f"{uptime/3600:.1f}h" if uptime > 3600 else f"{uptime/60:.1f}m"
                    st.metric("Session Uptime", uptime_str)
                else:
                    st.metric("Session Uptime", "N/A")
            
            with session_col2:
                st.metric("Requests Processed", session_metrics.get('requests_processed', 0))
            
            with session_col3:
                st.metric("Errors Encountered", session_metrics.get('errors_encountered', 0))
            
            # Last activity
            if session_metrics.get('last_activity'):
                last_activity = session_metrics['last_activity']
                if isinstance(last_activity, pd.Timestamp):
                    time_since = pd.Timestamp.now() - last_activity
                    st.info(f"Last activity: {time_since.total_seconds():.0f} seconds ago")
        
        # Log Files Section
        st.subheader("📋 Log Files")
        
        log_files = self._get_available_log_files()
        if log_files:
            selected_log = st.selectbox("Select Log File", log_files)
            
            if st.button("View Log"):
                self._display_log_file(selected_log)
        else:
            st.info("No log files found")
        
        # System Information
        with st.expander("🖥️ System Information", expanded=False):
            import platform
            
            sys_info = {
                'Platform': platform.platform(),
                'Python Version': platform.python_version(),
                'Architecture': platform.architecture()[0],
                'Processor': platform.processor() or 'Unknown',
                'Working Directory': os.getcwd(),
                'Environment': os.getenv('APP_ENV', 'development')
            }
            
            for key, value in sys_info.items():
                st.text(f"{key}: {value}")
    
    def _get_available_log_files(self) -> List[str]:
        """Get list of available log files."""
        log_files = []
        
        # Check common log locations
        log_locations = ['logs/', './']
        log_patterns = ['*.log', 'app.log', '*_errors.log', '*_performance.log']
        
        for location in log_locations:
            if os.path.exists(location):
                try:
                    for file in os.listdir(location):
                        if file.endswith('.log'):
                            log_files.append(os.path.join(location, file))
                except Exception:
                    continue
        
        return sorted(log_files)
    
    def _display_log_file(self, log_file: str, max_lines: int = 100) -> None:
        """Display contents of a log file."""
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Show last N lines
            recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines
            
            st.text_area(
                f"Last {len(recent_lines)} lines from {log_file}",
                value=''.join(recent_lines),
                height=400,
                key=f"log_display_{log_file}"
            )
            
            # Download button
            st.download_button(
                "Download Full Log",
                data=''.join(lines),
                file_name=os.path.basename(log_file),
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"Could not read log file: {e}")


# Global monitor instance
app_monitor = ApplicationMonitor()


def get_monitor() -> ApplicationMonitor:
    """Get the global application monitor instance."""
    return app_monitor


def record_operation_metric(operation: str, duration: float, success: bool, **kwargs) -> None:
    """
    Convenience function to record an operation metric.
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        success: Whether the operation was successful
        **kwargs: Additional data to include in the metric
    """
    app_monitor.record_metric(operation, duration, success, kwargs)


# Decorator for automatic performance monitoring
def monitor_performance(operation_name: str):
    """Decorator to automatically monitor function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                # Re-raise the exception after recording the metric
                raise
            finally:
                duration = time.time() - start_time
                app_monitor.record_metric(
                    operation=operation_name,
                    duration=duration,
                    success=success,
                    additional_data={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                )
        
        return wrapper
    return decorator