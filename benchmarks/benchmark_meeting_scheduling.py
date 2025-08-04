#!/usr/bin/env python3

import json, sys, time, traceback, click, requests

from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import defaultdict
import statistics


@dataclass
class BenchmarkConfig:
    """Configuration for the benchmark tool."""
    python_base_url: str = "http://127.0.0.1:8081"
    python2_base_url: str = "http://127.0.0.1:8082"
    java_base_url: str = "http://127.0.0.1:8080"
    

@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    data_source: str
    job_id: str
    solve_time_ms: int
    final_score: Dict[str, int]
    solver_iterations: int
    success: bool
    analysis: Optional[Dict] = None
    error_message: Optional[str] = None


@click.command()
@click.option('--iterations', default=1, help='Number of iterations per test')
@click.option('--output-file', type=click.Path(), help='Output results to markdown file')
@click.option('--test', help='Run only a specific test by name')
def main(iterations, output_file, test):
    """Meeting Scheduler Benchmark Tool"""
    config = BenchmarkConfig()
    
    click.echo("\n🔧 Meeting Scheduler Benchmark Tool")
    click.echo("="*50)
    
    # Check both servers
    python_server_ok = check_server(config.python_base_url)
    python2_server_ok = check_server(config.python2_base_url)
    java_server_ok = check_server(config.java_base_url)
    
    if not python_server_ok:
        click.echo(f"❌ Python server not running at {config.python_base_url}")
        click.echo("   Please start the Python server first with:")
        click.echo(f"   uvicorn src.meeting_scheduling:app --host {config.python_base_url.split('//')[1].split(':')[0]} --port {config.python_base_url.split(':')[-1]}")
    
    if not python2_server_ok:
        click.echo(f"❌ Python2 server not running at {config.python2_base_url}")
        click.echo("   Please start the Python2 server first with:")
        click.echo(f"   uvicorn src.meeting_scheduling:app --host {config.python2_base_url.split('//')[1].split(':')[0]} --port {config.python2_base_url.split(':')[-1]}")
    
    if not java_server_ok:
        click.echo(f"❌ Java server not running at {config.java_base_url}")
        click.echo("   Please start the Java server first")
    
    if not python_server_ok and not python2_server_ok and not java_server_ok:
        # Still write to file if requested, even if servers are down
        if output_file:
            click.echo(f"📄 Writing error status to {output_file}")
            with open(output_file, 'w') as f:
                f.write("# Meeting Scheduler Benchmark Results\n\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("## ❌ Server Error\n\n")
                f.write("No servers running:\n")
                f.write(f"- Python server: {config.python_base_url}\n")
                f.write(f"- Python2 server: {config.python2_base_url}\n")
                f.write(f"- Java server: {config.java_base_url}\n")
                
        sys.exit(1)
    
    if python_server_ok:
        click.echo(f"✅ Python server is running at {config.python_base_url}")

    if python2_server_ok:
        click.echo(f"✅ Python2 server is running at {config.python2_base_url}")

    if java_server_ok:
        click.echo(f"✅ Java server is running at {config.java_base_url}")
    
    click.echo()  # Add spacing after server status
    
    # Define test scenarios
    test_scenarios = {
        "Python Backend - Python Demo Data": {
            "condition": python_server_ok,
            "fetcher": lambda: get_demo_data(config.python_base_url),
            "converter": None,
            "backend": config.python_base_url
        },
        "Python Backend - Java Demo Data": {
            "condition": python_server_ok and java_server_ok,
            "fetcher": lambda: get_demo_data(config.java_base_url),
            "converter": lambda data: convert_java_to_python_format(data),
            "backend": config.python_base_url
        },
        "Python Backend (FAST) - Python Demo Data": {
            "condition": python2_server_ok,
            "fetcher": lambda: get_demo_data(config.python2_base_url),
            "converter": None,
            "backend": config.python2_base_url
        },
        "Python Backend (FAST) - Java Demo Data": {
            "condition": python2_server_ok and java_server_ok,
            "fetcher": lambda: get_demo_data(config.java_base_url),
            "converter": lambda data: convert_java_to_python_format(data),
            "backend": config.python2_base_url
        },
        "Java Backend - Java Demo Data": {
            "condition": java_server_ok,
            "fetcher": lambda: get_demo_data(config.java_base_url),
            "converter": None,
            "backend": config.java_base_url
        },
        "Java Backend - Python Demo Data": {
            "condition": java_server_ok and python_server_ok,
            "fetcher": lambda: get_demo_data(config.python_base_url),
            "converter": lambda data: convert_python_to_java_format(data),
            "backend": config.java_base_url
        }
    }

    all_results = []
    
    # Run tests
    if test:
        if test in test_scenarios:
            scenario = test_scenarios[test]
            if scenario['condition']:
                results = run_test_scenario(
                    test, 
                    scenario['fetcher'], 
                    scenario['converter'], 
                    scenario['backend'], 
                    iterations
                )
                all_results.extend(results)
            else:
                click.echo(f"⚠️  Skipping test '{test}' - required server not running.")
        else:
            click.echo(f"❌ Unknown test: {test}")
            click.echo(f"   Available tests: {list(test_scenarios.keys())}")
    else:
        # Run all applicable tests
        for name, scenario in test_scenarios.items():
            if scenario['condition']:
                results = run_test_scenario(
                    name, 
                    scenario['fetcher'], 
                    scenario['converter'], 
                    scenario['backend'], 
                    iterations
                )
                all_results.extend(results)

    print_results(all_results, output_file)


def run_test_scenario(test_name, data_fetcher, data_converter=None, target_backend=None, iterations=1):
    """Generic test runner using closures to avoid repetition."""
    click.echo(f"📥 Testing {test_name}...")
    click.echo("-" * 60)
    
    def analyze_solution(data, backend, original_data=None):
        """Analyze solution with detailed output following proper REST API flow."""
        click.echo(f"   🔍 Analyzing final solution...")
        
        # Step 1: Get the complete solution from the solver (REST API step 4)
        solved_data = data
        if hasattr(result, 'job_id') and result.job_id:
            try:
                click.echo(f"   📥 Fetching complete solution for job {result.job_id}...")
                response = requests.get(f"{backend}/schedules/{result.job_id}")

                if response.status_code == 200:
                    solved_data = response.json()
                    click.echo(f"   ✅ Retrieved solved schedule for analysis")

                else:
                    click.echo(f"   ⚠️ Could not retrieve solved schedule (status {response.status_code})")
                    click.echo(f"   ⚠️ Using input data for analysis")

            except Exception as e:
                click.echo(f"   ⚠️ Error retrieving solved schedule: {e}")
                click.echo(f"   ⚠️ Using input data for analysis")
        
        # Step 2: Prepare analysis payload (fix data if needed for cross-format scenarios)
        analysis_payload = solved_data
        if original_data:
            analysis_payload = prepare_for_analysis(solved_data, original_data)

        # Step 3: Call /analyze endpoint with the SOLUTION data (REST API step 5)
        click.echo(f"   🔬 Calling /analyze endpoint with solution data...")
        analysis = analyze_schedule(analysis_payload, backend)

        if analysis:
            constraint_count = len(analysis.get('constraints', []))
            click.echo(f"   📊 Analysis complete. Found {constraint_count} constraints.")
            return analysis
        
        else:
            click.echo(f"   ❌ Analysis failed")
            return None
    
    results = []
    for i in range(iterations):
        click.echo(f"\n   📥 Fetching demo data for iteration {i+1}...")
        
        # Fetch data using the provided closure
        demo_data = data_fetcher()
        
        if demo_data:
            click.echo(f"   ✅ Got demo data with {len(demo_data.get('meetings', []))} meetings")
            
            # Keep a copy of the original data before any conversion
            original_demo_data = json.loads(json.dumps(demo_data))
            
            # Convert data if converter is provided
            if data_converter:
                demo_data = data_converter(demo_data)
            
            # Run benchmark
            result = run_benchmark(demo_data, f"{test_name} (Run {i+1})", target_backend)
            
            # Analyze the final solution and store it
            if result.success:
                # For Java -> Python conversion, we need to use the original data for analysis
                if "Java Demo Data" in test_name and "Python Backend" in test_name:
                    analysis_result = analyze_solution(demo_data, target_backend, original_data=original_demo_data)

                else:
                    analysis_result = analyze_solution(demo_data, target_backend)

                result.analysis = analysis_result

            results.append(result)

        else:
            click.echo(f"   ❌ Failed to get demo data for iteration {i+1}")
            # Add a failed result
            results.append(BenchmarkResult(
                data_source=f"{test_name} (Run {i+1})",
                job_id="",
                solve_time_ms=0,
                final_score={},
                solver_iterations=0,
                success=False,
                error_message="Failed to get demo data"
            ))

    click.echo()  # Add spacing after test
    return results


def write_markdown_file(results: List[BenchmarkResult], output_file: str):
    """Write results to markdown file with maximum spiff."""
    def create_header():
        """Create spiff markdown header."""
        return [
            "# 🎯 Meeting Scheduler Benchmark Results",
            "",
            f"📅 **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"🚀 **Total Scenarios:** {len(results)}  ",
            f"✅ **Successful Runs:** {len([r for r in results if r.success])}  ",
            "",
            "---",
            ""
        ]
    
    def create_results_table():
        """Create spiff results table."""
        lines = [
            "## 📊 Individual Results",
            "",
            "| 🏷️ Scenario | 📈 Status | ⚡ Time | 🎯 Score | 🔄 Iterations | ❌ Error |",
            "|-------------|-----------|---------|----------|---------------|----------|"
        ]
        
        for result in results:
            status_icon = "🟢" if result.success else "🔴"
            status_text = "Success" if result.success else "Failed"
            
            if result.success:
                # Add performance indicators
                time_indicator = "🚀" if result.solve_time_ms < 25000 else "⚡" if result.solve_time_ms < 35000 else "🐌"
                lines.append(f"| **{result.data_source}** | {status_icon} {status_text} | {time_indicator} {result.solve_time_ms:,}ms | `{format_score(result.final_score)}` | {result.solver_iterations} | - |")
            
            else:
                lines.append(f"| **{result.data_source}** | {status_icon} {status_text} | - | - | - | {result.error_message} |")
        
        return lines
    
    def create_summary():
        """Create spiff comparison summary."""
        successful_results = [r for r in results if r.success]
        if len(successful_results) >= 2:
            # FIX: Use max() for best score since higher is better in constraint solving!
            best_result = max(successful_results, key=lambda r: calculate_total_score(r.final_score))
            fastest_result = min(successful_results, key=lambda r: r.solve_time_ms)
            times = [r.solve_time_ms for r in successful_results]
            avg_time = sum(times) / len(times)
            
            lines = [
                "",
                "## 🏆 Performance Summary",
                "",
                "### 🥇 Champion Results",
                "",
                f"**🏆 Best Score Champion:** `{best_result.data_source}`  ",
                f"📊 Score: `{format_score(best_result.final_score)}`  ",
                f"⏱️ Time: {best_result.solve_time_ms:,}ms  ",
                f"🔄 Iterations: {best_result.solver_iterations}  ",
                "",
                f"**⚡ Speed Champion:** `{fastest_result.data_source}`  ",
                f"⏱️ Time: {fastest_result.solve_time_ms:,}ms  ",
                f"📊 Score: `{format_score(fastest_result.final_score)}`  ",
                f"🔄 Iterations: {fastest_result.solver_iterations}  ",
                "",
                "### 📈 Performance Analytics",
                "",
                f"🎯 **Average Solve Time:** {avg_time:.0f}ms  ",
                f"📊 **Time Range:** {min(times):,}ms → {max(times):,}ms  ",
                f"🚀 **Total Scenarios:** {len(successful_results)}  ",
                ""
            ]
            return lines
        
        return []
    
    def create_cv_analysis():
        """Create coefficient of variation analysis for markdown."""
        grouped_results = group_results_by_scenario(results)
        scenarios_with_multiple_runs = {k: v for k, v in grouped_results.items() if len(v) > 1}
        
        if not scenarios_with_multiple_runs:
            return []
        
        lines = [
            "",
            "## 📊 Consistency Analysis (Coefficient of Variation)",
            "",
            "### 📈 Reliability Metrics",
            "",
            "| 🏷️ Scenario | 🔄 Runs | ⏱️ Avg Time | 📊 CV Time | 🎯 Avg Score | 📊 CV Score |",
            "|-------------|---------|-------------|------------|--------------|-------------|"
        ]
        
        for scenario_name, scenario_results in scenarios_with_multiple_runs.items():
            successful_runs = [r for r in scenario_results if r.success]
            if len(successful_runs) < 2:
                continue
                
            times = [r.solve_time_ms for r in successful_runs]
            scores = [calculate_total_score(r.final_score) for r in successful_runs]
            
            avg_time = statistics.mean(times)
            cv_time = calculate_coefficient_of_variation(times)
            avg_score = statistics.mean(scores)
            cv_score = calculate_coefficient_of_variation(scores)
            
            # Add consistency indicators
            time_consistency = "🟢" if cv_time < 10 else "🟡" if cv_time < 25 else "🔴"
            score_consistency = "🟢" if cv_score < 5 else "🟡" if cv_score < 15 else "🔴"
            
            lines.append(f"| **{scenario_name}** | {len(successful_runs)} | {avg_time:.0f}ms | {time_consistency} {cv_time:.1f}% | {avg_score:.0f} | {score_consistency} {cv_score:.1f}% |")
        
        lines.extend([
            "",
            "### 💡 CV Interpretation Guide",
            "",
            "- **🟢 Excellent consistency**: < 10% for time, < 5% for score",
            "- **🟡 Good consistency**: < 25% for time, < 15% for score", 
            "- **🔴 High variability**: > 25% for time, > 15% for score",
            "",
            "> **Coefficient of Variation (CV)** measures relative variability: `CV = (Standard Deviation / Mean) × 100%`",
            ""
        ])
        
        return lines
    
    def create_detailed_analysis():
        """Create spiff detailed constraint analysis."""
        lines = [
            "",
            "## 🔬 Detailed Constraint Analysis",
            ""
        ]
        
        for result in results:
            if result.success and result.analysis:
                lines.extend([
                    f"### 🎯 {result.data_source}",
                    "",
                    f"📊 **Final Score:** `{format_score(result.final_score)}`  ",
                    f"⏱️ **Solve Time:** {result.solve_time_ms:,}ms  ",
                    f"🔄 **Iterations:** {result.solver_iterations}  ",
                    ""
                ])
                
                # Add constraint breakdown from /analyze endpoint
                constraints = result.analysis.get('constraints', [])
                if constraints:
                    lines.extend([
                        "#### 🔍 Constraint Breakdown",
                        "",
                        "| 🏷️ Constraint | 📊 Score | 🎯 Impact |",
                        "|---------------|----------|-----------|"
                    ])
                    
                    for constraint in constraints:
                        name = constraint.get('name', 'Unknown')
                        score = format_score(constraint.get('score', {'hardScore': 0, 'mediumScore': 0, 'softScore': 0}))
                        
                        # Determine impact level with spiff indicators
                        constraint_score = constraint.get('score', {})
                        
                        # Handle both dict and string score formats
                        if isinstance(constraint_score, dict):
                            hard_score = constraint_score.get('hardScore', 0)
                            medium_score = constraint_score.get('mediumScore', 0)
                            soft_score = constraint_score.get('softScore', 0)

                        elif isinstance(constraint_score, str):
                            # Parse string format like "0hard/-5medium/-100soft"
                            try:
                                parts = constraint_score.split('/')
                                hard_score = int(parts[0].replace('hard', '')) if 'hard' in parts[0] else 0
                                medium_score = int(parts[1].replace('medium', '')) if len(parts) > 1 and 'medium' in parts[1] else 0
                                soft_score = int(parts[2].replace('soft', '')) if len(parts) > 2 and 'soft' in parts[2] else 0
                            
                            except:
                                hard_score = medium_score = soft_score = 0
                        
                        else:
                            hard_score = medium_score = soft_score = 0
                        
                        # Determine impact based on parsed scores
                        match (hard_score, medium_score, soft_score):
                            case (h, _, _) if h != 0:
                                impact = "🔴 Critical"

                            case (_, m, _) if m != 0:
                                impact = "🟡 Medium"

                            case (_, _, s) if s < -1000:
                                impact = "🟠 High"

                            case (_, _, s) if s < -100:
                                impact = "🟢 Low"

                            case _:
                                impact = "⚪ Minimal"
                        
                        lines.append(f"| {name} | `{score}` | {impact} |")
                    
                    lines.append("")
                
                # Add any additional analysis data
                if 'summary' in result.analysis:
                    lines.extend([
                        f"💡 **Summary:** {result.analysis['summary']}",
                        ""
                    ])
                
                lines.append("---")
                lines.append("")
        
        return lines
    
    click.echo(f"📝 Writing spiff markdown to: {output_file}")
    
    # Use closures to build output with maximum spiff
    output_lines = []
    output_lines.extend(create_header())
    
    successful_results = [r for r in results if r.success]
    if not successful_results:
        output_lines.extend([
            "## ❌ No Successful Runs",
            "",
            "🚨 **All benchmark scenarios failed!**  ",
            "🔧 Check server connectivity and data format compatibility.",
            ""
        ])

    else:
        output_lines.extend(create_results_table())
        output_lines.extend(create_summary())
        output_lines.extend(create_cv_analysis())
        output_lines.extend(create_detailed_analysis())
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(output_lines))
        click.echo(f"✅ Spiff benchmark report saved: {output_file}")

    except Exception as e:
        click.echo(f"❌ Error writing markdown file: {e}")
        traceback.print_exc()


def calculate_coefficient_of_variation(values: List[float]) -> float:
    """Calculate coefficient of variation (CV = std_dev / mean)."""
    if not values or len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    std_dev = statistics.stdev(values)
    return (std_dev / mean) * 100  # Return as percentage


def group_results_by_scenario(results: List[BenchmarkResult]) -> Dict[str, List[BenchmarkResult]]:
    """Group benchmark results by test scenario name."""
    grouped = defaultdict(list)
    for result in results:
        # Extract base scenario name (remove iteration numbers)
        base_name = result.data_source.split(" (Run ")[0]
        grouped[base_name].append(result)
    return dict(grouped)


def print_results(results: List[BenchmarkResult], output_file: Optional[str] = None):
    """Print benchmark results in a nice format and optionally save to markdown file."""
    def print_individual_results():
        """Print individual results."""
        click.echo("\n📊 Individual Results:")
        click.echo("-" * 40)
        
        for result in results:
            click.echo(f"\n🔸 {result.data_source}")
            click.echo(f"   Status: {'✅ Success' if result.success else '❌ Failed'}")
            
            if result.success:
                click.echo(f"   Time: {result.solve_time_ms:,}ms")
                click.echo(f"   Score: {format_score(result.final_score)}")
                click.echo(f"   Iterations: {result.solver_iterations}")
            else:
                click.echo(f"   Error: {result.error_message}")
            click.echo(f"   {'-' * 30}")
    
    def print_comparison_summary():
        """Print comparison summary."""
        successful_results = [r for r in results if r.success]
        if len(successful_results) >= 2:
            click.echo(f"\n🔄 COMPARISON SUMMARY")
            click.echo("-" * 40)
            
            # Find best and fastest results - HIGHER score is better in constraint solving!
            best_result = max(successful_results, key=lambda r: calculate_total_score(r.final_score))
            fastest_result = min(successful_results, key=lambda r: r.solve_time_ms)
            
            click.echo(f"🏆 Best Score: {best_result.data_source}")
            click.echo(f"   {format_score(best_result.final_score)} in {best_result.solve_time_ms:,}ms")
            click.echo(f"   {'-' * 30}")
            
            click.echo(f"\n⚡ Fastest Solve: {fastest_result.data_source}")
            click.echo(f"   {fastest_result.solve_time_ms:,}ms with score {format_score(fastest_result.final_score)}")
            click.echo(f"   {'-' * 30}")
            
            # Speed comparison
            times = [r.solve_time_ms for r in successful_results]
            avg_time = sum(times) / len(times)
            click.echo(f"\n📈 Average solve time: {avg_time:.0f}ms")
    
    def print_cv_analysis():
        """Print coefficient of variation analysis for consistency."""
        click.echo(f"\n📊 CONSISTENCY ANALYSIS (Coefficient of Variation)")
        click.echo(f"------------------------------------------------")
        
        grouped_results = group_results_by_scenario(results)
        scenarios_with_multiple_runs = {k: v for k, v in grouped_results.items() if len(v) > 1}
        
        if not scenarios_with_multiple_runs:
            click.echo("❗ CV analysis unavailable - no scenarios with multiple runs")
            return
        
        click.echo(f"{'Scenario':<50} {'Runs':<6} {'Avg Time':<12} {'CV Time':<10} {'Avg Score':<15} {'CV Score':<10}")
        click.echo(f"{'-' * 48:<50} {'-' * 4:<6} {'-' * 10:<12} {'-' * 8:<10} {'-' * 13:<15} {'-' * 8:<10}")
        
        for scenario_name, scenario_results in scenarios_with_multiple_runs.items():
            successful_runs = [r for r in scenario_results if r.success]
            if len(successful_runs) < 2:
                continue
                
            times = [r.solve_time_ms for r in successful_runs]
            scores = [calculate_total_score(r.final_score) for r in successful_runs]
            
            avg_time = statistics.mean(times)
            cv_time = calculate_coefficient_of_variation(times)
            avg_score = statistics.mean(scores)
            cv_score = calculate_coefficient_of_variation(scores)
            
            # Add consistency indicators
            time_consistency = "🟢" if cv_time < 10 else "🟡" if cv_time < 25 else "🔴"
            score_consistency = "🟢" if cv_score < 5 else "🟡" if cv_score < 15 else "🔴"
            
            click.echo(f"{scenario_name[:48]:<50} {len(successful_runs):<6} {avg_time:>8.0f}ms {time_consistency} {cv_time:>6.1f}% {avg_score:>12.0f} {score_consistency} {cv_score:>6.1f}%")
        
        click.echo(f"\n💡 CV Interpretation:")
        click.echo(f"   🟢 Excellent consistency (< 10% for time, < 5% for score)")
        click.echo(f"   🟡 Good consistency (< 25% for time, < 15% for score)")
        click.echo(f"   🔴 High variability (> 25% for time, > 15% for score)")

    def print_constraint_analysis():
        """Print constraint analysis."""
        click.echo(f"\n🔬 CONSTRAINT ANALYSIS")
        click.echo(f"----------------------------------------")
        
        # Find any Python backend result with analysis data
        python_results = [r for r in results if ("Python Backend" in r.data_source or "Python2 Backend" in r.data_source) and r.analysis]
        
        if not python_results:
            click.echo("❗ Constraint analysis unavailable - no Python backend results with analysis data")
            return
        
        # Use the first available Python backend result with analysis
        python_result = python_results[0]
        click.echo(f"📊 Analysis from: {python_result.data_source}")
        click.echo(f"{'Constraint':<40} {'Score':<15}")
        click.echo(f"{'-' * 38:<40} {'-' * 13:<15}")

        python_constraints = {c['name']: c for c in python_result.analysis.get('constraints', [])}

        for name in sorted(python_constraints.keys()):
            python_constraint = python_constraints.get(name, {})
            python_score = format_score(python_constraint.get('score', {'hardScore': 0, 'mediumScore': 0, 'softScore': 0})) if python_constraint else "N/A"
            click.echo(f"❗ {name:<38} {python_score:<15}")

    # Console output
    click.echo("\n" + "="*80)
    click.echo("🏁 BENCHMARK RESULTS")
    click.echo("="*80)
    
    successful_results = [r for r in results if r.success]
    
    if not successful_results:
        click.echo("❌ No successful benchmark runs!")
        if output_file:
            write_markdown_file(results, output_file)
        return
    
    # Use closures for printing
    print_individual_results()
    print_comparison_summary()
    print_cv_analysis()
    print_constraint_analysis()
    
    # Write to markdown file if requested
    if output_file:
        write_markdown_file(results, output_file)


def run_benchmark(data: Dict, data_source: str, base_url: str) -> BenchmarkResult:
    """Run a single benchmark with the given data."""
    def log_data_structure():
        """Log data structure details with spiff style."""
        click.echo(f"   🎯 Data Overview: {len(data.get('meetings', []))} meetings")
        
        if data.get('meetings'):
            # Show sample meetings with correct mapping
            sample_meetings = data['meetings'][:3]
            total_req = 0
            total_pref = 0
            
            for meeting in sample_meetings:
                req_count = len(meeting.get('requiredAttendances', []))
                pref_count = len(meeting.get('preferredAttendances', []))
                total_req += req_count
                total_pref += pref_count
                
                # Clean status indicators
                req_status = "✨" if req_count > 0 else "⚪"
                
                click.echo(f"   {req_status} Meeting {meeting.get('id')}: {req_count} required, {pref_count} preferred")
            
            # Show totals with appropriate format indicators
            if "8080" in base_url:  # Java backend - nested format
                click.echo(f"   📊 Total attendances: {total_req + total_pref} (nested in meetings)")

            else:  # Python backend - top-level format  
                top_req = len(data.get('requiredAttendances', []))
                top_pref = len(data.get('preferredAttendances', []))
                click.echo(f"   📊 Total attendances: {top_req + top_pref} ({top_req} required + {top_pref} preferred)")

    click.echo(f"\n⚡ Running {data_source}...")
    click.echo(f"   {'-' * 50}")
    
    # Clean data structure overview
    log_data_structure()
    click.echo(f"   {'-' * 50}")
    
    try:
        # If calling the Python backend ensure a 30-second termination limit so iteration counts are comparable
        if "8081" in base_url and "solverConfiguration" not in data:
            import copy
            data = copy.deepcopy(data)
            data["solverConfiguration"] = {
                "termination": {
                    "secondsSpentLimit": 30,
                    "unimprovedSecondsSpentLimit": 30
                }
            }
        
        # Submit the job
        response = requests.post(f"{base_url}/schedules", json=data)
        
        if response.status_code != 200:
            error_message = f"Job submission failed: {response.status_code}"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_message += f" - {error_data['message']}"
            except:
                error_message += f" - Response: {response.text[:200]}"
            return BenchmarkResult(
                data_source=data_source,
                job_id="",
                solve_time_ms=0,
                final_score={},
                solver_iterations=0,
                success=False,
                error_message=error_message
            )
        
        job_id = response.text.strip('"')
        click.echo(f"   🚀 Job launched: {job_id}")
        
        # Monitor solving progress with spiff progress indicators
        iterations = 0
        last_score = None
        solve_start_time = time.time()
        progress_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        
        while True:
            time.sleep(0.5)  # Check every 500ms
            iterations += 1
            
            response = requests.get(f"{base_url}/schedules/{job_id}/status")
            if response.status_code != 200:
                error_message = f"Status check failed: {response.status_code}"
                try:
                    error_data = response.json()

                    if 'message' in error_data:
                        error_message += f" - {error_data['message']}"

                except:
                    pass

                return BenchmarkResult(
                    data_source=data_source,
                    job_id=job_id,
                    solve_time_ms=0,
                    final_score={},
                    solver_iterations=iterations,
                    success=False,
                    error_message=error_message
                )
            
            status_data = response.json()
            solver_status = status_data.get('solverStatus')
            current_score = status_data.get('score', {})
            
            # Show progress with spiff spinner and score updates
            if current_score != last_score and current_score:
                spinner = progress_chars[iterations % len(progress_chars)]
                click.echo(f"   {spinner} Optimizing... {current_score}")
                last_score = current_score
            
            if solver_status == "NOT_SOLVING":
                solve_end_time = time.time()
                solve_time_ms = int((solve_end_time - solve_start_time) * 1000)
                
                click.echo(f"   ✅ Completed: {solve_time_ms:,}ms • {iterations} iterations • {format_score(current_score)}")
                
                return BenchmarkResult(
                    data_source=data_source,
                    job_id=job_id,
                    solve_time_ms=solve_time_ms,
                    final_score=current_score,
                    solver_iterations=iterations,
                    success=True
                )
            
            # Safety timeout (60 seconds)
            if time.time() - solve_start_time > 60:
                return BenchmarkResult(
                    data_source=data_source,
                    job_id=job_id,
                    solve_time_ms=0,
                    final_score=current_score,
                    solver_iterations=iterations,
                    success=False,
                    error_message="Timeout after 60 seconds"
                )
    
    except Exception as e:
        return BenchmarkResult(
            data_source=data_source,
            job_id="",
            solve_time_ms=0,
            final_score={},
            solver_iterations=0,
            success=False,
            error_message=str(e)
        )


def analyze_schedule(data: Dict, base_url: str) -> Optional[Dict]:
    """Analyze a schedule to get detailed constraint information."""
    try:
        response = requests.put(f"{base_url}/schedules/analyze", json=data, timeout=30)
        if response.status_code == 200:
            return response.json()
        
        else:
            click.echo(f"   ❌ Analysis failed with status {response.status_code}: {response.text}")
            return None
        
    except Exception as e:
        click.echo(f"   ❌ Analysis error: {e}")
        return None


def format_score(score: Dict[str, int] | str) -> str:
    """Format score for display."""
    def format_dict_score(score_dict):
        """Format dictionary scores."""
        hard = score_dict.get('hardScore', 0)
        medium = score_dict.get('mediumScore', 0)
        soft = score_dict.get('softScore', 0)
        return f"{hard}hard/{medium}medium/{soft}soft"
    
    def format_string_score(score_str):
        """Format string scores."""
        return score_str
    
    return format_dict_score(score) if isinstance(score, dict) else format_string_score(score)


def calculate_total_score(score: Dict[str, int] | str) -> int:
    """Calculate total weighted score."""
    def parse_score():
        """Parse score into components."""
        match score:
            case str():
                try:
                    parts = score.split('/')
                    hard = int(parts[0].replace('hard', ''))
                    medium = int(parts[1].replace('medium', ''))
                    soft = int(parts[2].replace('soft', ''))
                    return hard, medium, soft
                
                except:
                    return 0, 0, 0
                
            case dict():
                hard = score.get('hardScore', 0)
                medium = score.get('mediumScore', 0) 
                soft = score.get('softScore', 0)
                return hard, medium, soft
            
            case _:
                return 0, 0, 0
    
    def calculate_weighted_score(hard, medium, soft):
        """Calculate weighted score."""
        match (hard, medium, soft):
            case (h, _, _) if h != 0:
                return h * 1000000  # Hard constraints are most critical
            
            case (_, m, _) if m != 0:
                return m * 1000     # Medium constraints are second priority
            
            case (_, _, s):
                return s            # Soft constraints for optimization
    
    hard, medium, soft = parse_score()
    return calculate_weighted_score(hard, medium, soft)


def prepare_for_analysis(solved_data: Dict, original_data: Dict) -> Dict:
    """Prepare solved data for analysis by re-injecting and fixing original nested lists."""
    def fix_attendance_person(attendance, people_by_id):
        """Fix person field in attendance."""
        if isinstance(attendance.get('person'), str):
            person_id = attendance['person']
            attendance['person'] = people_by_id.get(person_id, {"id": person_id, "fullName": f"Person {person_id}"})

        return attendance

    analysis_payload = solved_data.copy()
    
    # Create lookups
    people_by_id = {p['id']: p for p in original_data.get('people', [])}
    original_meetings = {m['id']: m for m in original_data.get('meetings', [])}
    
    # Re-inject and fix nested attendances for analysis
    for meeting in analysis_payload.get('meetings', []):
        if meeting['id'] in original_meetings:
            original_meeting = original_meetings[meeting['id']]
            
            # Deep copy and fix required attendances
            required_attendances = json.loads(json.dumps(original_meeting.get('requiredAttendances', [])))
            
            for attendance in required_attendances:
                fix_attendance_person(attendance, people_by_id)
            
            meeting['requiredAttendances'] = required_attendances
            
            # Deep copy and fix preferred attendances
            preferred_attendances = json.loads(json.dumps(original_meeting.get('preferredAttendances', [])))
            
            for attendance in preferred_attendances:
                fix_attendance_person(attendance, people_by_id)
            
            meeting['preferredAttendances'] = preferred_attendances
    
    return analysis_payload


def convert_python_to_java_format(python_data: Dict) -> Dict:
    """Convert Python-generated JSON to Java server format."""
    
    def group_attendances_by_meeting(attendances):
        """Group attendances by meeting ID."""
        grouped = {}
        
        for attendance in attendances:
            meeting_id = attendance.get('meeting')
            if meeting_id:
                if meeting_id not in grouped:
                    grouped[meeting_id] = []
                
                # Remove the meeting field and add to the meeting's list
                attendance_copy = attendance.copy()
                del attendance_copy['meeting']
                
                # Convert person object to string ID if needed
                if isinstance(attendance_copy.get('person'), dict):
                    attendance_copy['person'] = attendance_copy['person']['id']
                
                grouped[meeting_id].append(attendance_copy)
        
        return grouped

    # Convert the data
    converted = python_data.copy()
    
    # Set solver status if missing or null
    if converted.get('solverStatus') is None:
        converted['solverStatus'] = 'NOT_SOLVING'
    
    # Convert meetings to include nested attendances
    if 'meetings' in converted:
        # Group attendances by meeting
        required_attendances_by_meeting = group_attendances_by_meeting(converted.get('requiredAttendances', []))
        preferred_attendances_by_meeting = group_attendances_by_meeting(converted.get('preferredAttendances', []))
        
        # Add attendances to each meeting
        for meeting in converted['meetings']:
            meeting_id = meeting['id']
            meeting['requiredAttendances'] = required_attendances_by_meeting.get(meeting_id, [])
            meeting['preferredAttendances'] = preferred_attendances_by_meeting.get(meeting_id, [])
        
        # Remove the top-level attendance arrays
        if 'requiredAttendances' in converted:
            del converted['requiredAttendances']

        if 'preferredAttendances' in converted:
            del converted['preferredAttendances']
    
    # Remove the top-level attendance arrays - Java doesn't expect them

    return converted


def convert_java_to_python_format(java_data: Dict) -> Dict:
    """Convert Java-generated JSON to Python server format - BULLETPROOF VERSION!"""
    
    # START FRESH - no copying, no references, pure reconstruction
    python_data = {}
    
    # Copy scalar fields - NEVER PASS None VALUES!
    # Python domain uses snake_case solver_status, not camelCase solverStatus!
    solver_status_value = java_data.get("solverStatus")

    if solver_status_value is None or solver_status_value == "null":
        python_data["solver_status"] = "NOT_SOLVING"

    else:
        python_data["solver_status"] = solver_status_value
    
    if java_data.get("score") is not None:
        python_data["score"] = java_data["score"]
    
    # Build person lookup for attendance resolution
    people_lookup = {}
    if 'people' in java_data:
        for person in java_data['people']:
            people_lookup[person['id']] = {
                "id": person['id'],
                "fullName": person.get('fullName', f"Person {person['id']}")
            }
    
    # Copy all non-meeting arrays exactly as-is
    for field in ['people', 'rooms', 'timeGrains', 'meetingAssignments']:
        if field in java_data:
            python_data[field] = json.loads(json.dumps(java_data[field]))
    
    # THE CRITICAL PART: Process meetings and attendances with ZERO data loss
    python_data['meetings'] = []
    python_data['requiredAttendances'] = []
    python_data['preferredAttendances'] = []
    
    if 'meetings' in java_data:
        for java_meeting in java_data['meetings']:
            # Build new meeting structure
            python_meeting = {
                "id": java_meeting['id'],
                "topic": java_meeting.get('topic', f"Meeting {java_meeting['id']}"),
                "durationInGrains": java_meeting.get('durationInGrains', 1),
                "speakers": java_meeting.get('speakers') or [],
                "content": java_meeting.get('content') or "",
                "entireGroupMeeting": java_meeting.get('entireGroupMeeting', False),
                "requiredAttendances": [],
                "preferredAttendances": []
            }
            
            # Process REQUIRED attendances - extract every single one
            java_required = java_meeting.get('requiredAttendances') or []
            for java_att in java_required:
                # Extract person ID safely
                if isinstance(java_att.get('person'), str):
                    person_id = java_att['person']

                elif isinstance(java_att.get('person'), dict):
                    person_id = java_att['person']['id']

                else:
                    continue  # Skip malformed attendance
                
                # Get full person data
                person_obj = people_lookup.get(person_id, {
                    "id": person_id, 
                    "fullName": f"Person {person_id}"
                })
                
                # Create attendance record with ALL required fields
                attendance_record = {
                    "id": java_att['id'],
                    "meeting": java_meeting['id'],
                    "person": person_obj
                }
                
                # Add to BOTH places - this is crucial!
                python_meeting['requiredAttendances'].append(attendance_record)
                python_data['requiredAttendances'].append(attendance_record)
            
            # Process PREFERRED attendances - extract every single one  
            java_preferred = java_meeting.get('preferredAttendances') or []
            for java_att in java_preferred:
                # Extract person ID safely
                if isinstance(java_att.get('person'), str):
                    person_id = java_att['person']

                elif isinstance(java_att.get('person'), dict):
                    person_id = java_att['person']['id']

                else:
                    continue  # Skip malformed attendance
                
                # Get full person data
                person_obj = people_lookup.get(person_id, {
                    "id": person_id, 
                    "fullName": f"Person {person_id}"
                })
                
                # Create attendance record with ALL required fields
                attendance_record = {
                    "id": java_att['id'],
                    "meeting": java_meeting['id'],
                    "person": person_obj
                }
                
                # Add to BOTH places - this is crucial!
                python_meeting['preferredAttendances'].append(attendance_record)
                python_data['preferredAttendances'].append(attendance_record)
            
            python_data['meetings'].append(python_meeting)
    
    return python_data


def get_demo_data(base_url: str) -> Optional[Dict]:
    """Get fresh demo data from the server."""
    try:
        response = requests.get(f"{base_url}/demo-data")
        
        if response.status_code == 200:
            return response.json()
        
        else:
            click.echo(f"❌ Failed to get demo data: {response.status_code}")
            return None
        
    except Exception as e:
        click.echo(f"❌ Error getting demo data: {e}")
        return None


def check_server(base_url: str) -> bool:
    """Check if the server is running."""
    try:
        response = requests.get(f"{base_url}/demo-data", timeout=5)
        return response.status_code == 200
    
    except requests.ConnectionError:
        return False


if __name__ == "__main__":
    main()