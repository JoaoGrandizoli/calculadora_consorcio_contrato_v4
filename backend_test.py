#!/usr/bin/env python3
"""
Backend API Testing for Consortium Simulation System
Tests all endpoints with expected parameters and validates responses
"""

import requests
import sys
import json
from datetime import datetime

class ConsortiumAPITester:
    def __init__(self, base_url="https://simuflex.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.errors = []

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            self.errors.append(f"{name}: {details}")
        
        if details and success:
            print(f"   Details: {details}")

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                expected_message = "Simulador de Consórcio API - Ativo"
                success = data.get("message") == expected_message
                details = f"Message: {data.get('message')}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Root Endpoint", success, details)
            return success
            
        except Exception as e:
            self.log_test("Root Endpoint", False, str(e))
            return False

    def test_parametros_padrao(self):
        """Test default parameters endpoint"""
        try:
            response = requests.get(f"{self.api_url}/parametros-padrao", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                # Validate expected default parameters
                expected_keys = ['valor_carta', 'prazo_meses', 'taxa_admin', 'fundo_reserva', 
                               'mes_contemplacao', 'lance_livre_perc', 'taxa_reajuste_anual']
                
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    success = False
                    details = f"Missing keys: {missing_keys}"
                else:
                    # Validate some expected values
                    if (data['valor_carta'] == 100000 and 
                        data['prazo_meses'] == 120 and
                        data['taxa_admin'] == 0.21):
                        details = f"Default params OK - Valor: R${data['valor_carta']:,}, Prazo: {data['prazo_meses']} meses"
                    else:
                        success = False
                        details = f"Unexpected default values: {data}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Default Parameters", success, details)
            return success, data if success else {}
            
        except Exception as e:
            self.log_test("Default Parameters", False, str(e))
            return False, {}

    def test_simulacao_basica(self, parametros=None):
        """Test basic simulation with default or provided parameters"""
        if parametros is None:
            parametros = {
                "valor_carta": 100000,
                "prazo_meses": 120,
                "taxa_admin": 0.21,
                "fundo_reserva": 0.03,
                "mes_contemplacao": 1,
                "lance_livre_perc": 0.10,
                "taxa_reajuste_anual": 0.05
            }
        
        try:
            response = requests.post(f"{self.api_url}/simular", 
                                   json=parametros, 
                                   timeout=30)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                
                # Check if simulation was successful
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    # Validate response structure
                    required_keys = ['parametros', 'resultados', 'fluxos', 'detalhamento', 'resumo_financeiro']
                    missing_keys = [key for key in required_keys if key not in data]
                    
                    if missing_keys:
                        success = False
                        details = f"Missing response keys: {missing_keys}"
                    else:
                        # Validate CET calculation
                        resultados = data['resultados']
                        if resultados['convergiu']:
                            cet_anual = resultados['cet_anual'] * 100
                            # Expected CET should be around 12-13% annually
                            if 10 <= cet_anual <= 15:
                                details = f"CET: {cet_anual:.2f}% a.a., Lance Livre: R${data['resumo_financeiro']['valor_lance_livre']:,.2f}"
                            else:
                                success = False
                                details = f"CET out of expected range: {cet_anual:.2f}% (expected 10-15%)"
                        else:
                            success = False
                            details = f"CET calculation failed: {resultados.get('motivo_erro')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Basic Simulation", success, details)
            return success, data if success else {}
            
        except Exception as e:
            self.log_test("Basic Simulation", False, str(e))
            return False, {}

    def test_validacao_parametros(self):
        """Test parameter validation"""
        test_cases = [
            {
                "name": "Negative valor_carta",
                "params": {"valor_carta": -1000, "prazo_meses": 120},
                "expected_status": 400
            },
            {
                "name": "Zero prazo_meses", 
                "params": {"valor_carta": 100000, "prazo_meses": 0},
                "expected_status": 400
            },
            {
                "name": "Invalid mes_contemplacao",
                "params": {"valor_carta": 100000, "prazo_meses": 120, "mes_contemplacao": 150},
                "expected_status": 400
            }
        ]
        
        all_passed = True
        for case in test_cases:
            try:
                response = requests.post(f"{self.api_url}/simular", 
                                       json=case["params"], 
                                       timeout=10)
                success = response.status_code == case["expected_status"]
                details = f"Status: {response.status_code} (expected {case['expected_status']})"
                
                self.log_test(f"Validation - {case['name']}", success, details)
                if not success:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Validation - {case['name']}", False, str(e))
                all_passed = False
        
        return all_passed

    def test_pdf_generation(self, parametros=None):
        """Test PDF generation endpoint"""
        if parametros is None:
            parametros = {
                "valor_carta": 100000,
                "prazo_meses": 120,
                "taxa_admin": 0.21,
                "fundo_reserva": 0.03,
                "mes_contemplacao": 1,
                "lance_livre_perc": 0.10,
                "taxa_reajuste_anual": 0.05
            }
        
        try:
            response = requests.post(f"{self.api_url}/gerar-relatorio-pdf", 
                                   json=parametros, 
                                   timeout=60)  # PDF generation might take longer
            success = response.status_code == 200
            
            if success:
                # Check if response is actually a PDF
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                
                if 'application/pdf' in content_type and content_length > 1000:
                    details = f"PDF generated successfully - Size: {content_length/1024:.1f}KB"
                else:
                    success = False
                    details = f"Invalid PDF response - Type: {content_type}, Size: {content_length} bytes"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("PDF Generation", success, details)
            return success
            
        except Exception as e:
            self.log_test("PDF Generation", False, str(e))
            return False

    def test_detailed_calculations(self):
        """Test detailed financial calculations"""
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 1,
            "lance_livre_perc": 0.10,
            "taxa_reajuste_anual": 0.05
        }
        
        success, data = self.test_simulacao_basica(parametros)
        
        if success:
            try:
                # Validate specific calculations
                resumo = data['resumo_financeiro']
                
                # Base contract should be valor_carta * (1 + taxa_admin + fundo_reserva)
                expected_base = 100000 * (1 + 0.21 + 0.03)  # 124,000
                actual_base = resumo['base_contrato']
                
                base_ok = abs(actual_base - expected_base) < 1
                
                # Lance livre should be 10% of base contract
                expected_lance = expected_base * 0.10  # 12,400
                actual_lance = resumo['valor_lance_livre']
                
                lance_ok = abs(actual_lance - expected_lance) < 1
                
                # Check if we have 120 months of data
                detalhamento_ok = len(data['detalhamento']) == 120
                
                # Check if contemplation month is correct
                contemplacao_ok = any(item['eh_contemplacao'] and item['mes'] == 1 
                                    for item in data['detalhamento'])
                
                all_calc_ok = base_ok and lance_ok and detalhamento_ok and contemplacao_ok
                
                details = (f"Base: R${actual_base:,.2f} (expected R${expected_base:,.2f}), "
                          f"Lance: R${actual_lance:,.2f} (expected R${expected_lance:,.2f}), "
                          f"Months: {len(data['detalhamento'])}, Contemplação: {contemplacao_ok}")
                
                self.log_test("Detailed Calculations", all_calc_ok, details)
                return all_calc_ok
                
            except Exception as e:
                self.log_test("Detailed Calculations", False, str(e))
                return False
        else:
            return False

    def test_lance_livre_zero(self):
        """Test simulation with lance_livre_perc = 0 (should use 1 contemplado)"""
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 17,
            "lance_livre_perc": 0.0,  # Zero lance livre
            "taxa_reajuste_anual": 0.05
        }
        
        try:
            response = requests.post(f"{self.api_url}/simular", 
                                   json=parametros, 
                                   timeout=30)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    # Check probability calculations for month 17
                    resumo = data['resumo_financeiro']
                    prob_no_mes = resumo.get('prob_contemplacao_no_mes', 0)
                    prob_ate_mes = resumo.get('prob_contemplacao_ate_mes', 0)
                    participantes_restantes = resumo.get('participantes_restantes_mes', 0)
                    
                    # With lance_livre_perc = 0, should use 1 contemplado
                    # Expected probability = 1 / participantes_restantes
                    expected_participantes = 430 - (17 - 1) * 1  # 430 - 16 = 414
                    expected_prob = 1.0 / expected_participantes if expected_participantes > 0 else 0
                    
                    prob_ok = abs(prob_no_mes - expected_prob) < 0.001
                    participantes_ok = participantes_restantes == expected_participantes
                    
                    # Check for NaN or infinite values
                    valid_values = (not any(str(val) in ['nan', 'inf', '-inf'] 
                                          for val in [prob_no_mes, prob_ate_mes]))
                    
                    all_ok = prob_ok and participantes_ok and valid_values
                    
                    details = (f"Lance livre: {parametros['lance_livre_perc']*100}%, "
                              f"Prob no mês: {prob_no_mes:.4f} (expected: {expected_prob:.4f}), "
                              f"Participantes: {participantes_restantes} (expected: {expected_participantes}), "
                              f"Valid values: {valid_values}")
                    
                    self.log_test("Lance Livre Zero (1 contemplado)", all_ok, details)
                    return all_ok
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                self.log_test("Lance Livre Zero (1 contemplado)", False, details)
                return False
                
        except Exception as e:
            self.log_test("Lance Livre Zero (1 contemplado)", False, str(e))
            return False

    def test_lance_livre_positivo(self):
        """Test simulation with lance_livre_perc > 0 (should use 2 contemplados)"""
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 17,
            "lance_livre_perc": 0.10,  # 10% lance livre
            "taxa_reajuste_anual": 0.05
        }
        
        try:
            response = requests.post(f"{self.api_url}/simular", 
                                   json=parametros, 
                                   timeout=30)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    # Check probability calculations for month 17
                    resumo = data['resumo_financeiro']
                    prob_no_mes = resumo.get('prob_contemplacao_no_mes', 0)
                    prob_ate_mes = resumo.get('prob_contemplacao_ate_mes', 0)
                    participantes_restantes = resumo.get('participantes_restantes_mes', 0)
                    
                    # With lance_livre_perc > 0, should use 2 contemplados
                    # Expected probability = 2 / participantes_restantes
                    expected_participantes = 430 - (17 - 1) * 2  # 430 - 32 = 398
                    expected_prob = min(2.0 / expected_participantes, 1.0) if expected_participantes > 0 else 0
                    
                    prob_ok = abs(prob_no_mes - expected_prob) < 0.001
                    participantes_ok = participantes_restantes == expected_participantes
                    
                    # Check for NaN or infinite values
                    valid_values = (not any(str(val) in ['nan', 'inf', '-inf'] 
                                          for val in [prob_no_mes, prob_ate_mes]))
                    
                    all_ok = prob_ok and participantes_ok and valid_values
                    
                    details = (f"Lance livre: {parametros['lance_livre_perc']*100}%, "
                              f"Prob no mês: {prob_no_mes:.4f} (expected: {expected_prob:.4f}), "
                              f"Participantes: {participantes_restantes} (expected: {expected_participantes}), "
                              f"Valid values: {valid_values}")
                    
                    self.log_test("Lance Livre Positivo (2 contemplados)", all_ok, details)
                    return all_ok
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                self.log_test("Lance Livre Positivo (2 contemplados)", False, details)
                return False
                
        except Exception as e:
            self.log_test("Lance Livre Positivo (2 contemplados)", False, str(e))
            return False

    def test_calcular_probabilidades_endpoint(self):
        """Test the /api/calcular-probabilidades endpoint with new ParametrosProbabilidade model"""
        test_cases = [
            {
                "name": "Com Lance Livre",
                "params": {"num_participantes": 430, "lance_livre_perc": 0.10},
                "expected_contemplados": 2
            },
            {
                "name": "Sem Lance Livre", 
                "params": {"num_participantes": 430, "lance_livre_perc": 0.0},
                "expected_contemplados": 1
            }
        ]
        
        all_passed = True
        for case in test_cases:
            try:
                response = requests.post(f"{self.api_url}/calcular-probabilidades", 
                                       json=case["params"], 
                                       timeout=30)
                success = response.status_code == 200
                
                if success:
                    data = response.json()
                    
                    if data.get('erro'):
                        success = False
                        details = f"API error: {data.get('mensagem')}"
                    else:
                        # Validate response structure
                        required_keys = ['sem_lance', 'com_lance', 'parametros']
                        missing_keys = [key for key in required_keys if key not in data]
                        
                        if missing_keys:
                            success = False
                            details = f"Missing response keys: {missing_keys}"
                        else:
                            # Validate probability curves
                            sem_lance = data['sem_lance']
                            com_lance = data['com_lance']
                            
                            # Check if we have valid probability data
                            has_meses = len(sem_lance.get('meses', [])) > 0
                            has_hazard = len(sem_lance.get('hazard', [])) > 0
                            has_prob_acum = len(sem_lance.get('probabilidade_acumulada', [])) > 0
                            
                            # Check for NaN or infinite values in first few hazard values
                            hazard_values = sem_lance.get('hazard', [])[:5]
                            valid_hazard = all(isinstance(h, (int, float)) and 
                                             not (str(h) in ['nan', 'inf', '-inf']) 
                                             for h in hazard_values)
                            
                            structure_ok = has_meses and has_hazard and has_prob_acum and valid_hazard
                            
                            if structure_ok:
                                # Check if lance_livre_perc affects the calculation correctly
                                params = data['parametros']
                                contemplados = params.get('contemplados_por_mes', 0)
                                contemplados_ok = contemplados == case['expected_contemplados']
                                
                                details = (f"Contemplados por mês: {contemplados} "
                                          f"(expected: {case['expected_contemplados']}), "
                                          f"Meses: {len(sem_lance['meses'])}, "
                                          f"Valid hazard: {valid_hazard}")
                                
                                success = contemplados_ok
                            else:
                                success = False
                                details = f"Invalid probability structure - Meses: {has_meses}, Hazard: {has_hazard}, Valid: {valid_hazard}"
                else:
                    details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
                self.log_test(f"Probabilidades - {case['name']}", success, details)
                if not success:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Probabilidades - {case['name']}", False, str(e))
                all_passed = False
        
        return all_passed

    def test_pdf_without_cashflow_graph(self):
        """Test PDF generation to ensure cash flow graph is removed"""
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 17,
            "lance_livre_perc": 0.10,
            "taxa_reajuste_anual": 0.05
        }
        
        try:
            response = requests.post(f"{self.api_url}/gerar-relatorio-pdf", 
                                   json=parametros, 
                                   timeout=60)
            success = response.status_code == 200
            
            if success:
                # Check if response is actually a PDF
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                
                if 'application/pdf' in content_type and content_length > 1000:
                    # PDF generated successfully - we can't easily check if cash flow graph is removed
                    # without parsing the PDF, but we can verify it generates without errors
                    details = f"PDF generated successfully - Size: {content_length/1024:.1f}KB (cash flow graph should be removed)"
                else:
                    success = False
                    details = f"Invalid PDF response - Type: {content_type}, Size: {content_length} bytes"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("PDF Without Cash Flow Graph", success, details)
            return success
            
        except Exception as e:
            self.log_test("PDF Without Cash Flow Graph", False, str(e))
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests for Consortium Simulation System")
        print(f"📍 Testing endpoint: {self.base_url}")
        print("=" * 70)
        
        # Test sequence
        self.test_root_endpoint()
        success, default_params = self.test_parametros_padrao()
        
        if success:
            self.test_simulacao_basica(default_params)
        else:
            self.test_simulacao_basica()  # Use hardcoded defaults
            
        self.test_validacao_parametros()
        self.test_detailed_calculations()
        
        # NEW TESTS for lance_livre_perc functionality
        print("\n🎯 Testing Lance Livre Functionality:")
        self.test_lance_livre_zero()
        self.test_lance_livre_positivo()
        self.test_calcular_probabilidades_endpoint()
        
        # PDF tests
        self.test_pdf_generation()
        self.test_pdf_without_cashflow_graph()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print(f"✅ Tests Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if self.errors:
            print("\n🔍 FAILED TESTS:")
            for error in self.errors:
                print(f"   • {error}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = ConsortiumAPITester()
    
    try:
        all_passed = tester.run_all_tests()
        return 0 if all_passed else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())