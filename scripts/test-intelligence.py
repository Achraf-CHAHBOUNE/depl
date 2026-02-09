#!/usr/bin/env python3
"""
DGI INTELLIGENCE SERVICE - COMPLETE TEST SCRIPT
================================================

Tests all 6 official DGI use cases with UNPAID invoices.
Works with your actual API structure: POST /rules/compute

Author: DGI Compliance Team
Date: February 2026
Version: 2.0 (Fixed for unpaid scenarios)

Usage:
    python test_all_cases.py --url http://localhost:8004
    python test_all_cases.py --url http://localhost:8004 --verbose
    python test_all_cases.py --url http://localhost:8004 --export results.json

Requirements:
    pip install requests rich
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import argparse
import sys

# Pretty printing
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None
    def rprint(text):
        print(text)


# ============================================================================
# TEST CASES - All 6 DGI Official Cases
# ============================================================================

def generate_all_test_cases() -> List[Dict]:
    """Generate all 6 official DGI test cases as UNPAID invoices"""
    
    test_cases = []
    
    # ========================================================================
    # CAS PRATIQUE #1-1: Paid On Time (NO PENALTY)
    # ========================================================================
    test_cases.append({
        "case_number": "1-1",
        "case_name": "Paiement à Temps - Aucune Pénalité",
        "description": "Invoice paid BEFORE due date. NO penalty expected.",
        "invoice": {
            "invoice_id": "FAC-001",
            "supplier": {"name": "ACME SARL", "ice": "002345678000045"},
            "customer": {"name": "CLIENT SA", "ice": "001234567000001"},
            "invoice": {
                "number": "FAC-001",
                "issue_date": "2023-07-20",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 10169.50},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-001",
            "matches": [{
                "payment_id": "PAY-001",
                "matched_amount": 10169.50,
                "confidence_score": 100.0,
                "matching_reasons": ["Full payment"]
            }],
            "payment_status": "PAID",
            "total_paid": 10169.50,
            "remaining_amount": 0.0,
            "payment_dates": ["2023-09-10"]
        },
        "expected": {
            "due_date": "2023-09-18",
            "days_overdue": 0,
            "months_delay": 0,
            "penalty_rate": 0.0,
            "penalty_amount": 0.0
        }
    })
    
    # ========================================================================
    # CAS PRATIQUE #1-2: 1 Month Delay (UNPAID)
    # ========================================================================
    test_cases.append({
        "case_number": "1-2",
        "case_name": "1 Mois de Retard - 3.0%",
        "description": "Invoice 7 days overdue, UNPAID. Penalty = 3% × 10,169.50 = 305.09 MAD",
        "invoice": {
            "invoice_id": "FAC-002",
            "supplier": {"name": "ACME SARL", "ice": "002345678000045"},
            "customer": {"name": "CLIENT SA", "ice": "001234567000001"},
            "invoice": {
                "number": "FAC-002",
                "issue_date": "2023-07-20",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 10169.50},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-002",
            "matches": [],
            "payment_status": "UNPAID",
            "total_paid": 0.0,
            "remaining_amount": 10169.50,
            "payment_dates": ["2023-09-25"]
        },
        "expected": {
            "due_date": "2023-09-18",
            "days_overdue": 7,
            "months_delay": 1,
            "penalty_rate": 3.0,
            "penalty_amount": 305.09,
            "unpaid_amount": 10169.50
        }
    })
    
    # ========================================================================
    # CAS PRATIQUE #1-3: 2 Months Delay (UNPAID)
    # ========================================================================
    test_cases.append({
        "case_number": "1-3",
        "case_name": "2 Mois de Retard - 3.85%",
        "description": "Invoice 58 days overdue, UNPAID. Penalty = 3.85% × 10,169.50 = 391.52 MAD",
        "invoice": {
            "invoice_id": "FAC-003",
            "supplier": {"name": "ACME SARL", "ice": "002345678000045"},
            "customer": {"name": "CLIENT SA", "ice": "001234567000001"},
            "invoice": {
                "number": "FAC-003",
                "issue_date": "2023-07-20",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 10169.50},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-003",
            "matches": [],
            "payment_status": "UNPAID",
            "total_paid": 0.0,
            "remaining_amount": 10169.50,
            "payment_dates": ["2023-11-15"]
        },
        "expected": {
            "due_date": "2023-09-18",
            "days_overdue": 58,
            "months_delay": 2,
            "penalty_rate": 3.85,
            "penalty_amount": 391.52,
            "unpaid_amount": 10169.50
        }
    })
    
    # ========================================================================
    # CAS PRATIQUE #2: Contractual Delay 80 Days (UNPAID)
    # ========================================================================
    test_cases.append({
        "case_number": "2",
        "case_name": "Délai Contractuel 80j - 3.0%",
        "description": "Contract 80 days, 7 days overdue, UNPAID. Penalty = 3% × 50,847.46 = 1,525.42 MAD",
        "invoice": {
            "invoice_id": "FAC-BTP-001",
            "supplier": {"name": "BTP SARL", "ice": "002765432000089"},
            "customer": {"name": "CLIENT SA", "ice": "001234567000001"},
            "invoice": {
                "number": "FAC-BTP-001",
                "issue_date": "2023-07-20",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 50847.46},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-BTP-001",
            "matches": [],
            "payment_status": "UNPAID",
            "total_paid": 0.0,
            "remaining_amount": 50847.46,
            "payment_dates": ["2023-10-15"]
        },
        "contractual_delay_days": 80,
        "expected": {
            "due_date": "2023-10-09",
            "days_overdue": 6,
            "months_delay": 1,
            "penalty_rate": 3.0,
            "penalty_amount": 1525.42,
            "unpaid_amount": 50847.46
        }
    })
    
    # ========================================================================
    # CAS PRATIQUE #3: Service Completion Date (UNPAID)
    # ========================================================================
    test_cases.append({
        "case_number": "3",
        "case_name": "Service Fait - 3.0%",
        "description": "Service completion date, 7 days overdue, UNPAID. Penalty = 3% × 101,694.92 = 3,050.85 MAD",
        "invoice": {
            "invoice_id": "FAC-PUB-001",
            "supplier": {"name": "TRAVAUX PUBLICS SA", "ice": "002987654000123"},
            "customer": {"name": "MINISTERE", "ice": "001111111000001"},
            "invoice": {
                "number": "FAC-PUB-001",
                "issue_date": "2023-07-15",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 101694.92},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-PUB-001",
            "matches": [],
            "payment_status": "UNPAID",
            "total_paid": 0.0,
            "remaining_amount": 101694.92,
            "payment_dates": ["2023-09-25"]
        },
        "expected": {
            "due_date": "2023-09-18",
            "days_overdue": 7,
            "months_delay": 1,
            "penalty_rate": 3.0,
            "penalty_amount": 3050.85,
            "unpaid_amount": 101694.92
        }
    })
    
    # ========================================================================
    # CAS PRATIQUE #5: 2 Months Exact (UNPAID)
    # ========================================================================
    test_cases.append({
        "case_number": "5",
        "case_name": "2 Mois Exact - 3.85%",
        "description": "Exactly 2 months overdue (61 days), UNPAID. Penalty = 3.85% × 152,542.37 = 5,872.88 MAD",
        "invoice": {
            "invoice_id": "FAC-IND-005",
            "supplier": {"name": "EQUIPEMENTS SARL", "ice": "002111222000333"},
            "customer": {"name": "CLIENT SA", "ice": "001234567000001"},
            "invoice": {
                "number": "FAC-IND-005",
                "issue_date": "2023-07-20",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 152542.37},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-IND-005",
            "matches": [],
            "payment_status": "UNPAID",
            "total_paid": 0.0,
            "remaining_amount": 152542.37,
            "payment_dates": ["2023-11-18"]
        },
        "expected": {
            "due_date": "2023-09-18",
            "days_overdue": 61,
            "months_delay": 2,
            "penalty_rate": 3.85,
            "penalty_amount": 5872.88,
            "unpaid_amount": 152542.37
        }
    })
    
    # ========================================================================
    # CAS PRATIQUE #6: Max Contract 120 Days + 3 Months Delay (UNPAID)
    # ========================================================================
    test_cases.append({
        "case_number": "6",
        "case_name": "Délai Max 120j + 3 Mois - 4.70%",
        "description": "120-day contract, 3 months overdue, UNPAID. Penalty = 4.70% × 508,474.58 = 23,898.31 MAD",
        "invoice": {
            "invoice_id": "FAC-MEGA-001",
            "supplier": {"name": "MEGA CONSTRUCTION SA", "ice": "002444555000666"},
            "customer": {"name": "CLIENT SA", "ice": "001234567000001"},
            "invoice": {
                "number": "FAC-MEGA-001",
                "issue_date": "2023-07-20",
                "delivery_date": "2023-07-20"
            },
            "amounts": {"total_ttc": 508474.58},
            "line_items": [],
            "missing_fields": []
        },
        "matching_result": {
            "invoice_id": "FAC-MEGA-001",
            "matches": [],
            "payment_status": "UNPAID",
            "total_paid": 0.0,
            "remaining_amount": 508474.58,
            "payment_dates": ["2024-02-17"]
        },
        "contractual_delay_days": 120,
        "expected": {
            "due_date": "2023-11-17",
            "days_overdue": 92,
            "months_delay": 3,
            "penalty_rate": 4.70,
            "penalty_amount": 23898.31,
            "unpaid_amount": 508474.58
        }
    })
    
    return test_cases


# ============================================================================
# API CLIENT
# ============================================================================

class IntelligenceServiceClient:
    """Client for Intelligence Service API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def health_check(self) -> bool:
        """Check if service is running"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def compute_legal(self, test_case: Dict) -> Dict:
        """Send test case to /rules/compute endpoint"""
        
        payload = {
            "invoice": test_case["invoice"],
            "matching_result": test_case["matching_result"],
            "contractual_delay_days": test_case.get("contractual_delay_days"),
            "is_disputed": False,
            "is_credit_note": False,
            "is_procedure_690": False
        }
        
        # Add test_date if specified (for simulating "today")
        if "test_date" in test_case:
            payload["test_date"] = test_case["test_date"]
        
        try:
            response = self.session.post(
                f"{self.base_url}/rules/compute",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            return {
                "error": f"HTTP {e.response.status_code}",
                "detail": e.response.text
            }
        except Exception as e:
            return {
                "error": str(type(e).__name__),
                "detail": str(e)
            }


# ============================================================================
# TEST RUNNER
# ============================================================================

class TestRunner:
    """Runs all test cases and validates results"""
    
    def __init__(self, client: IntelligenceServiceClient, verbose: bool = False):
        self.client = client
        self.verbose = verbose
        self.results = []
    
    def run_test(self, test_case: Dict) -> Dict:
        """Run a single test case"""
        
        case_num = test_case["case_number"]
        case_name = test_case["case_name"]
        
        if HAS_RICH:
            console.print(f"\n[bold cyan]Test {case_num}:[/bold cyan] {case_name}")
            console.print(f"[dim]{test_case['description']}[/dim]")
        else:
            print(f"\n=== Test {case_num}: {case_name} ===")
            print(f"{test_case['description']}")
        
        # Call API
        api_result = self.client.compute_legal(test_case)
        
        if "error" in api_result:
            if HAS_RICH:
                console.print(f"[bold red]✗ API Error:[/bold red] {api_result['error']}")
            else:
                print(f"✗ API Error: {api_result['error']}")
            return {
                "case_number": case_num,
                "case_name": case_name,
                "status": "ERROR",
                "passed": False,
                "api_result": api_result,
                "expected": test_case["expected"]
            }
        
        # Compare results
        expected = test_case["expected"]
        comparison = self.compare(expected, api_result)
        
        # Display
        if self.verbose:
            self.display_detailed(comparison)
        else:
            self.display_summary(comparison)
        
        return {
            "case_number": case_num,
            "case_name": case_name,
            "status": "PASS" if comparison["all_passed"] else "FAIL",
            "passed": comparison["all_passed"],
            "api_result": api_result,
            "expected": expected,
            "comparison": comparison
        }
    
    def compare(self, expected: Dict, actual: Dict) -> Dict:
        """Compare expected vs actual values"""
        
        checks = []
        all_passed = True
        
        # Check each expected field
        test_cases = [
            ("Due Date", expected.get("due_date"), actual.get("legal_due_date")),
            ("Days Overdue", expected.get("days_overdue"), actual.get("days_overdue")),
            ("Months Delay", expected.get("months_delay"), actual.get("months_of_delay")),
            ("Penalty Rate %", expected.get("penalty_rate"), actual.get("penalty_rate")),
            ("Penalty Amount", expected.get("penalty_amount"), actual.get("penalty_amount"), 1.0),  # 1 MAD tolerance
            ("Unpaid Amount", expected.get("unpaid_amount"), actual.get("unpaid_amount"), 0.01),
        ]
        
        for check_name, exp_val, act_val, *tolerance in test_cases:
            if exp_val is None:
                continue
            
            tol = tolerance[0] if tolerance else None
            
            if tol and exp_val is not None and act_val is not None:
                passed = abs(float(exp_val) - float(act_val)) <= tol
            else:
                passed = str(exp_val) == str(act_val)
            
            checks.append({
                "name": check_name,
                "expected": exp_val,
                "actual": act_val,
                "passed": passed
            })
            
            if not passed:
                all_passed = False
        
        return {"all_passed": all_passed, "checks": checks}
    
    def display_summary(self, comparison: Dict):
        """Display pass/fail summary"""
        if comparison["all_passed"]:
            if HAS_RICH:
                console.print("[bold green]✓ PASSED[/bold green]")
            else:
                print("✓ PASSED")
        else:
            failed = [c for c in comparison["checks"] if not c["passed"]]
            if HAS_RICH:
                console.print(f"[bold red]✗ FAILED[/bold red] - {len(failed)} check(s):")
                for c in failed:
                    console.print(f"  [red]• {c['name']}:[/red] expected {c['expected']}, got {c['actual']}")
            else:
                print(f"✗ FAILED - {len(failed)} check(s):")
                for c in failed:
                    print(f"  • {c['name']}: expected {c['expected']}, got {c['actual']}")
    
    def display_detailed(self, comparison: Dict):
        """Display detailed comparison table"""
        if HAS_RICH:
            table = Table()
            table.add_column("Field", style="cyan")
            table.add_column("Expected", style="yellow")
            table.add_column("Actual", style="magenta")
            table.add_column("Status", style="bold")
            
            for c in comparison["checks"]:
                status = "[green]✓[/green]" if c["passed"] else "[red]✗[/red]"
                table.add_row(c["name"], str(c["expected"]), str(c["actual"]), status)
            
            console.print(table)
        else:
            print(f"\n  {'Field':<20} {'Expected':<15} {'Actual':<15} {'Status':<5}")
            print(f"  {'-'*60}")
            for c in comparison["checks"]:
                status = "✓" if c["passed"] else "✗"
                print(f"  {c['name']:<20} {str(c['expected']):<15} {str(c['actual']):<15} {status:<5}")
    
    def run_all(self, test_cases: List[Dict]):
        """Run all test cases"""
        
        if HAS_RICH:
            console.print("\n[bold blue]═══════════════════════════════════════════════════════[/bold blue]")
            console.print("[bold blue]   DGI INTELLIGENCE SERVICE - TEST SUITE[/bold blue]")
            console.print("[bold blue]═══════════════════════════════════════════════════════[/bold blue]")
        else:
            print("\n" + "="*60)
            print("   DGI INTELLIGENCE SERVICE - TEST SUITE")
            print("="*60)
        
        for test_case in test_cases:
            result = self.run_test(test_case)
            self.results.append(result)
        
        self.display_final_summary()
    
    def display_final_summary(self):
        """Display final summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        if HAS_RICH:
            console.print("\n[bold blue]═══════════════════════════════════════════════════════[/bold blue]")
            console.print("[bold blue]   FINAL SUMMARY[/bold blue]")
            console.print("[bold blue]═══════════════════════════════════════════════════════[/bold blue]\n")
            
            summary_table = Table()
            summary_table.add_column("Case", style="cyan")
            summary_table.add_column("Name", style="white")
            summary_table.add_column("Status", style="bold")
            
            for r in self.results:
                status = "[green]✓ PASS[/green]" if r["passed"] else "[red]✗ FAIL[/red]"
                summary_table.add_row(r["case_number"], r["case_name"], status)
            
            console.print(summary_table)
            
            console.print(f"\n[bold]Total:[/bold] {total}")
            console.print(f"[bold green]Passed:[/bold green] {passed}")
            console.print(f"[bold red]Failed:[/bold red] {failed}")
            console.print(f"[bold]Pass Rate:[/bold] {pass_rate:.1f}%\n")
            
            if pass_rate == 100:
                console.print("[bold green]🎉 ALL TESTS PASSED! System is DGI-compliant! 🎉[/bold green]\n")
            else:
                console.print(f"[bold yellow]⚠️  {failed} test(s) failed. Review above. ⚠️[/bold yellow]\n")
        else:
            print("\n" + "="*60)
            print("   FINAL SUMMARY")
            print("="*60 + "\n")
            
            for r in self.results:
                status = "✓ PASS" if r["passed"] else "✗ FAIL"
                print(f"{r['case_number']:<6} {r['case_name']:<40} {status}")
            
            print(f"\nTotal: {total}")
            print(f"Passed: {passed}")
            print(f"Failed: {failed}")
            print(f"Pass Rate: {pass_rate:.1f}%\n")
            
            if pass_rate == 100:
                print("🎉 ALL TESTS PASSED! System is DGI-compliant! 🎉\n")
            else:
                print(f"⚠️  {failed} test(s) failed. Review above. ⚠️\n")
    
    def export_json(self, filename: str):
        """Export results to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "test_run": {
                    "date": datetime.now().isoformat(),
                    "total": len(self.results),
                    "passed": sum(1 for r in self.results if r["passed"]),
                    "failed": sum(1 for r in self.results if not r["passed"])
                },
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ Results exported to: {filename}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test DGI Intelligence Service")
    parser.add_argument('--url', default='http://localhost:8004', help='Service URL')
    parser.add_argument('--verbose', '-v', action='store_true', help='Detailed output')
    parser.add_argument('--export', metavar='FILE', help='Export to JSON')
    args = parser.parse_args()
    
    # Client
    client = IntelligenceServiceClient(args.url)
    
    # Health check
    print(f"Connecting to: {args.url}")
    if not client.health_check():
        print(f"✗ Service not reachable at {args.url}")
        print("  Make sure Intelligence Service is running on port 8004")
        sys.exit(1)
    print("✓ Service is running\n")
    
    # Generate tests
    test_cases = generate_all_test_cases()
    print(f"Generated {len(test_cases)} test cases\n")
    
    # Run
    runner = TestRunner(client, verbose=args.verbose)
    runner.run_all(test_cases)
    
    # Export
    if args.export:
        runner.export_json(args.export)
    
    # Exit code
    sys.exit(0 if all(r["passed"] for r in runner.results) else 1)


if __name__ == "__main__":
    main()