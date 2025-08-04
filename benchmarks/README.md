# 🎯 Benchmark Framework Documentation

## 🚀 Setup Instructions

### 1. Start Backend Servers

```bash
# Terminal 1 - Original Python Backend
uvicorn src.meeting_scheduling:app --host 127.0.0.1 --port 8081

# Terminal 2 - Fast Python Backend  
uvicorn src.meeting_scheduling:app --host 127.0.0.1 --port 8082

# Terminal 3 - Java Backend
cd quickstarts/java/meeting-scheduling
mvn quarkus:dev

### 2. Run Benchmark

```bash
# Run all scenarios
python quickstarts/benchmark/benchmark_meeting_scheduling.py

# Run specific test
python quickstarts/benchmark/benchmark_meeting_scheduling.py --test "Python Backend (FAST) - Java Demo Data"

# Run with multiple iterations
python quickstarts/benchmark/benchmark_meeting_scheduling.py --iterations 5

# Save results to markdown file
python quickstarts/benchmark/benchmark_meeting_scheduling.py --output-file results.md
```

## 🛠️ Technical Implementation

### Benchmark Architecture

```python
@dataclass
class BenchmarkResult:
    data_source: str
    job_id: str
    solve_time_ms: int
    final_score: Dict[str, int]
    solver_iterations: int
    success: bool
    analysis: Optional[Dict] = None
    error_message: Optional[str] = None
```

### Data Conversion

#### Java → Python Format
- Extracts nested attendances from meetings
- Converts person references to full objects
- Maintains data integrity across platforms

#### Python → Java Format  
- Groups attendances by meeting ID
- Converts person objects to string IDs
- Adds nested attendance structures

### Solver Configuration
```python
"solverConfiguration": {
    "termination": {
        "secondsSpentLimit": 30,
        "unimprovedSecondsSpentLimit": 30
    }
}
```

## 📈 Performance Analysis

### Current Limitations
1. **Small Dataset**: Current demo data may be too small to reveal true performance differences
2. **Time Limits**: 30-second termination masks performance characteristics
3. **Memory Constraints**: Not currently measured

### Key Findings

**Performance Comparison:**
- **Java vs FAST Python**: Comparable performance (~0.5% difference)
- **Original Python**: Performance already degraded with fewer iterations completed (46-58 vs 60) and constraint evaluation bugs (-85medium violations)

**Theoretical Scaling Prediction:**
- **Original Python**: Validation overhead increases with dataset size (complexity unknown)
- **FAST Python/Java**: No validation overhead during solving

**Note:** Actual scaling behavior not yet measured.

## 🎯 Recommendations

### 1. **Architectural Recommendations**
- **Python Backend (FAST)** proves to be perfectly viable for production deployment for the Meeting Scheduling Problem with a small dataset
- **Java Backend** remains the reference implementation, with proven performance and correctness
- **Avoid Original Python Backend with Pydantic domain models** due to constraint evaluation bugs and incomplete optimization

In more detail:

- **Use dataclass domain models** for constraint solving implementations
- **Reserve Pydantic models** for API serialization/deserialization only
- **Maintain clean separation** between domain logic and validation logic
- **Monitor optimization completion rates** as a key performance indicator

## 🔧 Troubleshooting

### Common Issues

#### Server Connection Errors
```bash
❌ Python server not running at http://127.0.0.1:8081
   Please start the Python server first with:
   uvicorn src.meeting_scheduling:app --host 127.0.0.1 --port 8081
```

#### Data Conversion Errors
- Ensure both servers are running for cross-platform tests
- Check data format compatibility
- Verify constraint definitions match

#### Timeout Issues
- Increase solver termination limits for larger datasets
- Monitor system resources during solving
- Check for memory leaks in long-running sessions

## 📝 Output Formats

### Console Output
- Real-time progress indicators
- Detailed constraint analysis
- Performance comparison summary

### Markdown Output
- Comprehensive results table
- Performance analytics
- Detailed constraint breakdown
- Professional reporting format

## 🔄 Future Enhancements

### Research Areas
1. **Porting the benchmark to other problems**

### Planned Improvements
1. **Larger dataset generation**
2. **Memory usage tracking**
3. **Performance profiling**
4. **Regression testing**