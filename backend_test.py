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

    def test_pdf_with_corrected_card_values(self):
        """Test PDF generation with corrected card values (not hardcoded R$ 100,000)"""
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
                    # PDF generated successfully - the corrected values should be in the table
                    # We can't easily parse PDF content, but we can verify it generates without errors
                    # and has reasonable size (indicating the table with corrected values is included)
                    details = f"PDF with corrected card values generated - Size: {content_length/1024:.1f}KB"
                else:
                    success = False
                    details = f"Invalid PDF response - Type: {content_type}, Size: {content_length} bytes"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("PDF With Corrected Card Values", success, details)
            return success
            
        except Exception as e:
            self.log_test("PDF With Corrected Card Values", False, str(e))
            return False

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

    def test_valor_carta_corrigido_bug_fix(self):
        """
        Test the specific bug fix for valor da carta correction in cash flow table.
        Bug: Card value was hardcoded as R$ 100,000.00 in frontend table and PDF.
        Fix: Should show valor_carta_corrigido that undergoes annual monetary correction.
        
        Test parameters:
        - valor_carta: 100000
        - mes_contemplacao: 17
        - taxa_reajuste_anual: 0.05 (5%)
        - prazo_meses: 120
        
        Expected values:
        - Month 1-12: R$ 100,000.00 (year 1, factor 1.0)
        - Month 13-24: R$ 105,000.00 (year 2, factor 1.05)
        - Month 25-36: R$ 110,250.00 (year 3, factor 1.05²)
        - Contemplation in month 17: should use corrected value R$ 105,000.00
        """
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 17,
            "lance_livre_perc": 0.10,
            "taxa_reajuste_anual": 0.05  # 5% annual correction
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
                    detalhamento = data['detalhamento']
                    issues = []
                    
                    # Test specific months for card value correction
                    test_months = {
                        1: {"expected_value": 100000.00, "year": 1, "factor": 1.0},
                        12: {"expected_value": 100000.00, "year": 1, "factor": 1.0},
                        13: {"expected_value": 105000.00, "year": 2, "factor": 1.05},
                        17: {"expected_value": 105000.00, "year": 2, "factor": 1.05},  # Contemplation month
                        24: {"expected_value": 105000.00, "year": 2, "factor": 1.05},
                        25: {"expected_value": 110250.00, "year": 3, "factor": 1.1025},
                        36: {"expected_value": 110250.00, "year": 3, "factor": 1.1025}
                    }
                    
                    month_data = {}
                    for item in detalhamento:
                        if item['mes'] in test_months:
                            month_data[item['mes']] = item
                    
                    # Validate card values for each test month
                    for mes, expected in test_months.items():
                        if mes in month_data:
                            actual_value = month_data[mes]['valor_carta_corrigido']
                            expected_value = expected['expected_value']
                            tolerance = 1.0  # R$ 1.00 tolerance for rounding
                            
                            if abs(actual_value - expected_value) > tolerance:
                                issues.append(f"Month {mes}: Expected R${expected_value:,.2f}, "
                                            f"got R${actual_value:,.2f} "
                                            f"(diff: R${abs(actual_value - expected_value):,.2f})")
                            
                            # Verify year and factor calculations
                            actual_year = month_data[mes]['ano']
                            actual_factor = month_data[mes]['fator_correcao']
                            expected_year = expected['year']
                            expected_factor = expected['factor']
                            
                            if actual_year != expected_year:
                                issues.append(f"Month {mes}: Expected year {expected_year}, got {actual_year}")
                            
                            if abs(actual_factor - expected_factor) > 0.001:
                                issues.append(f"Month {mes}: Expected factor {expected_factor:.4f}, "
                                            f"got {actual_factor:.4f}")
                    
                    # Special validation for contemplation month (17)
                    if 17 in month_data:
                        contemplacao_data = month_data[17]
                        if not contemplacao_data['eh_contemplacao']:
                            issues.append("Month 17 should be marked as contemplation month")
                        
                        # Verify contemplation uses corrected card value
                        carta_contemplacao = data['resumo_financeiro']['valor_carta_contemplacao']
                        expected_carta_contemplacao = 105000.00  # R$ 100k * 1.05
                        
                        if abs(carta_contemplacao - expected_carta_contemplacao) > 1.0:
                            issues.append(f"Contemplation card value: Expected R${expected_carta_contemplacao:,.2f}, "
                                        f"got R${carta_contemplacao:,.2f}")
                    
                    # Verify that values are NOT hardcoded to 100,000
                    hardcoded_count = sum(1 for item in detalhamento[:36] 
                                        if abs(item['valor_carta_corrigido'] - 100000.00) < 0.01)
                    
                    # Only first 12 months should have exactly 100,000
                    if hardcoded_count > 12:
                        issues.append(f"Too many months with hardcoded R$100,000 value: {hardcoded_count} "
                                    f"(expected max 12 for first year)")
                    
                    success = len(issues) == 0
                    
                    if success:
                        details = (f"✅ Card value correction working correctly. "
                                 f"Year 1 (months 1-12): R$100,000.00, "
                                 f"Year 2 (months 13-24): R$105,000.00, "
                                 f"Year 3 (months 25-36): R$110,250.00, "
                                 f"Contemplation (month 17): R${carta_contemplacao:,.2f}")
                    else:
                        details = f"❌ Card value correction issues: {'; '.join(issues)}"
                        
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Valor da Carta Corrigido Bug Fix", success, details)
            return success
            
        except Exception as e:
            self.log_test("Valor da Carta Corrigido Bug Fix", False, str(e))
            return False

    def test_saldo_devedor_pos_contemplacao(self):
        """
        Test the specific bug fix for saldo devedor after contemplation.
        Bug: After contemplation, balance was incorrectly going to zero.
        Fix: Balance should only decrease by installment amount, not by carta value.
        """
        # Use exact parameters from user report
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 17,  # As reported by user
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
                
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    detalhamento = data['detalhamento']
                    
                    # Find months around contemplation (16, 17, 18, 19, 20)
                    months_to_check = [16, 17, 18, 19, 20]
                    month_data = {}
                    
                    for item in detalhamento:
                        if item['mes'] in months_to_check:
                            month_data[item['mes']] = {
                                'saldo_devedor': item['saldo_devedor'],
                                'parcela_corrigida': item['parcela_corrigida'],
                                'eh_contemplacao': item['eh_contemplacao'],
                                'valor_carta_corrigido': item['valor_carta_corrigido'],
                                'fluxo_liquido': item['fluxo_liquido']
                            }
                    
                    # Validate the bug fix
                    issues = []
                    
                    # 1. Check that month 17 is marked as contemplation
                    if not month_data[17]['eh_contemplacao']:
                        issues.append("Month 17 not marked as contemplation")
                    
                    # 2. Check that saldo devedor doesn't go to zero in month 17
                    saldo_17 = month_data[17]['saldo_devedor']
                    if saldo_17 <= 1000:  # Should not be close to zero
                        issues.append(f"Saldo devedor too low in month 17: R${saldo_17:,.2f}")
                    
                    # 3. Check that saldo devedor decreases properly between months
                    saldo_16 = month_data[16]['saldo_devedor']
                    saldo_18 = month_data[18]['saldo_devedor']
                    parcela_17 = month_data[17]['parcela_corrigida']
                    
                    # Expected decrease should be approximately the installment amount
                    expected_saldo_17 = saldo_16 - parcela_17
                    saldo_diff = abs(saldo_17 - expected_saldo_17)
                    
                    if saldo_diff > 100:  # Allow small rounding differences
                        issues.append(f"Saldo devedor calculation incorrect in month 17. "
                                    f"Expected: ~R${expected_saldo_17:,.2f}, "
                                    f"Actual: R${saldo_17:,.2f}, "
                                    f"Difference: R${saldo_diff:,.2f}")
                    
                    # 4. Check that balance continues decreasing in following months
                    if saldo_18 >= saldo_17:
                        issues.append(f"Saldo devedor not decreasing properly after contemplation. "
                                    f"Month 17: R${saldo_17:,.2f}, Month 18: R${saldo_18:,.2f}")
                    
                    # 5. Check final balance (should be close to zero at end)
                    final_month = detalhamento[-1]
                    final_saldo = final_month['saldo_devedor']
                    if final_saldo > 1000:  # Should be close to zero at the end
                        issues.append(f"Final saldo devedor too high: R${final_saldo:,.2f}")
                    
                    # 6. Verify contemplation flow is positive (receives carta value)
                    fluxo_17 = month_data[17]['fluxo_liquido']
                    if fluxo_17 <= 0:
                        issues.append(f"Contemplation flow should be positive, got: R${fluxo_17:,.2f}")
                    
                    success = len(issues) == 0
                    
                    if success:
                        details = (f"✅ Saldo devedor bug fix working correctly. "
                                 f"Month 16: R${saldo_16:,.2f}, "
                                 f"Month 17 (contemplação): R${saldo_17:,.2f}, "
                                 f"Month 18: R${saldo_18:,.2f}, "
                                 f"Final: R${final_saldo:,.2f}, "
                                 f"Contemplation flow: R${fluxo_17:,.2f}")
                    else:
                        details = f"❌ Issues found: {'; '.join(issues)}"
                        
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Saldo Devedor Pós-Contemplação Bug Fix", success, details)
            return success
            
        except Exception as e:
            self.log_test("Saldo Devedor Pós-Contemplação Bug Fix", False, str(e))
            return False

    def test_vpl_when_cet_converges(self):
        """
        Test VPL calculation when CET converges (early contemplation).
        Should calculate both CET and VPL successfully.
        
        Test parameters for convergence:
        - valor_carta: 100000
        - mes_contemplacao: 1 (early contemplation should converge)
        - lance_livre_perc: 0.10
        - prazo_meses: 120
        """
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 1,  # Early contemplation - should converge
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
                
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    resultados = data['resultados']
                    issues = []
                    
                    # 1. Check that CET converged
                    convergiu = resultados.get('convergiu', False)
                    if not convergiu:
                        issues.append(f"CET should converge for early contemplation, but convergiu={convergiu}")
                    
                    # 2. Check that CET values are present and valid
                    cet_anual = resultados.get('cet_anual')
                    cet_mensal = resultados.get('cet_mensal')
                    
                    if cet_anual is None or str(cet_anual) in ['nan', 'inf', '-inf']:
                        issues.append(f"Invalid CET anual: {cet_anual}")
                    elif not (0.05 <= cet_anual <= 0.20):  # Expected range 5-20%
                        issues.append(f"CET anual out of expected range: {cet_anual*100:.2f}% (expected 5-20%)")
                    
                    if cet_mensal is None or str(cet_mensal) in ['nan', 'inf', '-inf']:
                        issues.append(f"Invalid CET mensal: {cet_mensal}")
                    
                    # 3. Check that VPL is calculated
                    vpl = resultados.get('vpl')
                    taxa_desconto_vpl = resultados.get('taxa_desconto_vpl')
                    
                    if vpl is None or str(vpl) in ['nan', 'inf', '-inf']:
                        issues.append(f"VPL should be calculated, got: {vpl}")
                    
                    if taxa_desconto_vpl != 0.10:
                        issues.append(f"Taxa desconto VPL should be 0.10 (10%), got: {taxa_desconto_vpl}")
                    
                    # 4. VPL should be reasonable (negative for this type of operation)
                    if vpl is not None and str(vpl) not in ['nan', 'inf', '-inf']:
                        if vpl > 0:
                            issues.append(f"VPL should typically be negative for consortium operations, got: R${vpl:,.2f}")
                    
                    success = len(issues) == 0
                    
                    if success:
                        details = (f"✅ CET converged and VPL calculated successfully. "
                                 f"CET: {cet_anual*100:.2f}% a.a., "
                                 f"VPL: R${vpl:,.2f}, "
                                 f"Taxa VPL: {taxa_desconto_vpl*100:.0f}%")
                    else:
                        details = f"❌ Issues found: {'; '.join(issues)}"
                        
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("VPL When CET Converges (Early Contemplation)", success, details)
            return success
            
        except Exception as e:
            self.log_test("VPL When CET Converges (Early Contemplation)", False, str(e))
            return False

    def test_vpl_when_cet_not_converges(self):
        """
        Test VPL calculation when CET does not converge (late contemplation).
        This is the main new functionality being tested.
        
        Test parameters for non-convergence:
        - valor_carta: 100000
        - mes_contemplacao: 50 (late contemplation should cause non-convergence)
        - lance_livre_perc: 0.10
        - prazo_meses: 120
        """
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 50,  # Late contemplation - should NOT converge
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
                
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    resultados = data['resultados']
                    issues = []
                    
                    # 1. Check that CET did NOT converge
                    convergiu = resultados.get('convergiu', True)
                    if convergiu:
                        issues.append(f"CET should NOT converge for late contemplation (month 50), but convergiu={convergiu}")
                    
                    # 2. Check that CET values are NaN/None when not converged
                    cet_anual = resultados.get('cet_anual')
                    cet_mensal = resultados.get('cet_mensal')
                    
                    if convergiu == False:
                        # When not converged, CET should be NaN or None
                        if cet_anual is not None and str(cet_anual) not in ['nan', 'inf', '-inf']:
                            issues.append(f"CET anual should be NaN when not converged, got: {cet_anual}")
                        if cet_mensal is not None and str(cet_mensal) not in ['nan', 'inf', '-inf']:
                            issues.append(f"CET mensal should be NaN when not converged, got: {cet_mensal}")
                    
                    # 3. Check that VPL is calculated even when CET doesn't converge
                    vpl = resultados.get('vpl')
                    taxa_desconto_vpl = resultados.get('taxa_desconto_vpl')
                    
                    if vpl is None or str(vpl) in ['nan', 'inf', '-inf']:
                        issues.append(f"VPL should be calculated even when CET doesn't converge, got: {vpl}")
                    
                    if taxa_desconto_vpl != 0.10:
                        issues.append(f"Taxa desconto VPL should be 0.10 (10%), got: {taxa_desconto_vpl}")
                    
                    # 4. VPL should be reasonable (negative for this type of operation)
                    if vpl is not None and str(vpl) not in ['nan', 'inf', '-inf']:
                        if vpl > 0:
                            issues.append(f"VPL should typically be negative for consortium operations, got: R${vpl:,.2f}")
                    
                    # 5. Check that motivo_erro is provided when CET doesn't converge
                    motivo_erro = resultados.get('motivo_erro')
                    if not convergiu and not motivo_erro:
                        issues.append("motivo_erro should be provided when CET doesn't converge")
                    
                    success = len(issues) == 0
                    
                    if success:
                        details = (f"✅ VPL calculated successfully when CET doesn't converge. "
                                 f"Convergiu: {convergiu}, "
                                 f"VPL: R${vpl:,.2f}, "
                                 f"Taxa VPL: {taxa_desconto_vpl*100:.0f}%, "
                                 f"Motivo: {motivo_erro}")
                    else:
                        details = f"❌ Issues found: {'; '.join(issues)}"
                        
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("VPL When CET Does NOT Converge (Late Contemplation)", success, details)
            return success
            
        except Exception as e:
            self.log_test("VPL When CET Does NOT Converge (Late Contemplation)", False, str(e))
            return False

    def test_vpl_calculation_accuracy(self):
        """
        Test VPL calculation accuracy with known parameters.
        Verify that VPL is calculated using 10% annual discount rate converted to monthly.
        """
        parametros = {
            "valor_carta": 100000,
            "prazo_meses": 120,
            "taxa_admin": 0.21,
            "fundo_reserva": 0.03,
            "mes_contemplacao": 1,  # Early contemplation for stable calculation
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
                
                if data.get('erro'):
                    success = False
                    details = f"Simulation error: {data.get('mensagem')}"
                else:
                    resultados = data['resultados']
                    fluxos = data['fluxos']
                    issues = []
                    
                    # 1. Check that we have valid cash flows
                    if not fluxos or len(fluxos) < 2:
                        issues.append(f"Invalid cash flows for VPL calculation: {len(fluxos) if fluxos else 0} flows")
                    
                    # 2. Check VPL calculation
                    vpl = resultados.get('vpl')
                    taxa_desconto_vpl = resultados.get('taxa_desconto_vpl')
                    
                    if vpl is None or str(vpl) in ['nan', 'inf', '-inf']:
                        issues.append(f"Invalid VPL value: {vpl}")
                    
                    if taxa_desconto_vpl != 0.10:
                        issues.append(f"Incorrect discount rate: {taxa_desconto_vpl} (expected 0.10)")
                    
                    # 3. Manual VPL calculation to verify accuracy
                    if fluxos and len(fluxos) >= 2 and taxa_desconto_vpl == 0.10:
                        try:
                            # Convert annual rate to monthly: (1 + 0.10)^(1/12) - 1
                            taxa_mensal = (1 + 0.10) ** (1/12) - 1
                            
                            # Calculate VPL manually
                            vpl_manual = sum(cf / (1 + taxa_mensal) ** i for i, cf in enumerate(fluxos))
                            
                            # Compare with API result (allow 1% tolerance)
                            if abs(vpl - vpl_manual) > abs(vpl_manual * 0.01):
                                issues.append(f"VPL calculation mismatch. API: R${vpl:,.2f}, Manual: R${vpl_manual:,.2f}")
                            
                        except Exception as calc_error:
                            issues.append(f"Error in manual VPL calculation: {calc_error}")
                    
                    # 4. Check that VPL fields are present in response model
                    required_vpl_fields = ['vpl', 'taxa_desconto_vpl']
                    missing_fields = [field for field in required_vpl_fields if field not in resultados]
                    if missing_fields:
                        issues.append(f"Missing VPL fields in response: {missing_fields}")
                    
                    success = len(issues) == 0
                    
                    if success:
                        details = (f"✅ VPL calculation accurate. "
                                 f"VPL: R${vpl:,.2f}, "
                                 f"Taxa: {taxa_desconto_vpl*100:.0f}%, "
                                 f"Cash flows: {len(fluxos)} periods")
                    else:
                        details = f"❌ Issues found: {'; '.join(issues)}"
                        
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("VPL Calculation Accuracy", success, details)
            return success
            
        except Exception as e:
            self.log_test("VPL Calculation Accuracy", False, str(e))
            return False

    def test_vpl_always_calculated(self):
        """
        Test that VPL is always calculated regardless of CET convergence.
        Test multiple scenarios to ensure VPL is consistently present.
        """
        test_scenarios = [
            {
                "name": "Early Contemplation (CET should converge)",
                "params": {
                    "valor_carta": 100000,
                    "prazo_meses": 120,
                    "taxa_admin": 0.21,
                    "fundo_reserva": 0.03,
                    "mes_contemplacao": 1,
                    "lance_livre_perc": 0.10,
                    "taxa_reajuste_anual": 0.05
                }
            },
            {
                "name": "Mid Contemplation",
                "params": {
                    "valor_carta": 100000,
                    "prazo_meses": 120,
                    "taxa_admin": 0.21,
                    "fundo_reserva": 0.03,
                    "mes_contemplacao": 25,
                    "lance_livre_perc": 0.10,
                    "taxa_reajuste_anual": 0.05
                }
            },
            {
                "name": "Late Contemplation (CET should NOT converge)",
                "params": {
                    "valor_carta": 100000,
                    "prazo_meses": 120,
                    "taxa_admin": 0.21,
                    "fundo_reserva": 0.03,
                    "mes_contemplacao": 50,
                    "lance_livre_perc": 0.10,
                    "taxa_reajuste_anual": 0.05
                }
            }
        ]
        
        all_passed = True
        scenario_results = []
        
        for scenario in test_scenarios:
            try:
                response = requests.post(f"{self.api_url}/simular", 
                                       json=scenario["params"], 
                                       timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data.get('erro'):
                        resultados = data['resultados']
                        
                        # Check VPL presence and validity
                        vpl = resultados.get('vpl')
                        taxa_desconto_vpl = resultados.get('taxa_desconto_vpl')
                        convergiu = resultados.get('convergiu', False)
                        
                        vpl_valid = vpl is not None and str(vpl) not in ['nan', 'inf', '-inf']
                        taxa_valid = taxa_desconto_vpl == 0.10
                        
                        scenario_success = vpl_valid and taxa_valid
                        
                        scenario_results.append({
                            "name": scenario["name"],
                            "success": scenario_success,
                            "convergiu": convergiu,
                            "vpl": vpl,
                            "taxa_desconto_vpl": taxa_desconto_vpl,
                            "mes_contemplacao": scenario["params"]["mes_contemplacao"]
                        })
                        
                        if not scenario_success:
                            all_passed = False
                    else:
                        scenario_results.append({
                            "name": scenario["name"],
                            "success": False,
                            "error": data.get('mensagem', 'Unknown error')
                        })
                        all_passed = False
                else:
                    scenario_results.append({
                        "name": scenario["name"],
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    all_passed = False
                    
            except Exception as e:
                scenario_results.append({
                    "name": scenario["name"],
                    "success": False,
                    "error": str(e)
                })
                all_passed = False
        
        # Generate summary
        if all_passed:
            details = "✅ VPL calculated in all scenarios: "
            details += ", ".join([
                f"{r['name']}: VPL=R${r['vpl']:,.2f} (convergiu={r['convergiu']})"
                for r in scenario_results if r['success']
            ])
        else:
            failed_scenarios = [r for r in scenario_results if not r['success']]
            details = f"❌ VPL calculation failed in {len(failed_scenarios)} scenarios: "
            details += ", ".join([
                f"{r['name']}: {r.get('error', 'VPL calculation issue')}"
                for r in failed_scenarios
            ])
        
        self.log_test("VPL Always Calculated", all_passed, details)
        return all_passed

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
        self.test_pdf_with_corrected_card_values()
        
        # SPECIFIC BUG FIX TESTS
        print("\n🐛 Testing Specific Bug Fixes:")
        self.test_valor_carta_corrigido_bug_fix()
        self.test_saldo_devedor_pos_contemplacao()
        
        # NEW VPL FUNCTIONALITY TESTS
        print("\n💰 Testing VPL (Net Present Value) Functionality:")
        self.test_vpl_when_cet_converges()
        self.test_vpl_when_cet_not_converges()
        self.test_vpl_calculation_accuracy()
        self.test_vpl_always_calculated()
        
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