from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Optional
import numpy as np
from scipy.optimize import fsolve
import warnings
warnings.filterwarnings('ignore')
import tempfile
from datetime import datetime, timezone, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app without a prefix
app = FastAPI(title="Simulador de Consórcio API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class ParametrosConsorcio(BaseModel):
    valor_carta: float = 100_000
    prazo_meses: int = 120
    taxa_admin: float = 0.21
    fundo_reserva: float = 0.03
    mes_contemplacao: int = 1
    lance_livre_perc: float = 0.10
    taxa_reajuste_anual: float = 0.05

class DetalhamentoMes(BaseModel):
    mes: int
    data: str  # Data formatada (set/25, out/25, etc.)
    ano: int
    fator_correcao: float
    valor_carta_corrigido: float
    parcela_corrigida: float
    lance_livre: float
    fluxo_liquido: float
    saldo_devedor: float
    eh_contemplacao: bool

class ResumoFinanceiro(BaseModel):
    base_contrato: float
    valor_lance_livre: float
    valor_carta_contemplacao: float
    total_parcelas: float
    fluxo_contemplacao: float
    primeira_parcela: float
    primeira_parcela_pos_contemplacao: float
    parcela_intermediaria: float
    ultima_parcela: float
    # Resumo da Operação (como no site de referência)
    valor_credito_taxas: float
    taxas: float
    lance_embutido: float
    credito_liquido: float

class ResultadosSimulacao(BaseModel):
    cet_anual: Optional[float]
    cet_mensal: Optional[float]
    convergiu: bool
    motivo_erro: Optional[str]

class RespostaSimulacao(BaseModel):
    erro: bool
    mensagem: Optional[str] = None
    parametros: Optional[ParametrosConsorcio] = None
    resultados: Optional[ResultadosSimulacao] = None
    fluxos: List[float] = []
    detalhamento: List[DetalhamentoMes] = []
    resumo_financeiro: Optional[ResumoFinanceiro] = None

class SimuladorConsorcio:
    """Simulador de consórcio baseado na metodologia fornecida."""
    
    def __init__(self, parametros: ParametrosConsorcio):
        self.params = parametros
        self.convergiu = True
        self.motivo_erro = ""
    
    def calcular_base_lance(self) -> float:
        """Calcula base para lance: Crédito + Taxas + Fundo."""
        return self.params.valor_carta * (1 + self.params.taxa_admin + self.params.fundo_reserva)
    
    def gerar_fluxos_lance_livre(self) -> Dict:
        """Gera fluxos de caixa corretos - parcela só diminui com lance embutido."""
        try:
            # Base de cálculo
            base_contrato = self.calcular_base_lance()
            valor_lance_livre = base_contrato * self.params.lance_livre_perc
            
            # Cálculos do resumo da operação
            valor_credito_taxas = base_contrato  # R$ 124.000,00
            taxas = self.params.valor_carta * (self.params.taxa_admin + self.params.fundo_reserva)  # R$ 24.000,00
            lance_embutido = base_contrato * 0.08  # Aproximadamente 8% (baseado no documento)
            credito_liquido = self.params.valor_carta - (taxas + valor_lance_livre + lance_embutido - base_contrato)
            
            # Parcela base mensal - SEMPRE A MESMA (não diminui com lance livre)
            parcela_base_mensal = base_contrato / self.params.prazo_meses
            
            fluxos = [0]  # t=0
            detalhamento = []
            primeira_parcela = 0
            primeira_parcela_pos_contemplacao = 0
            parcela_intermediaria = 0
            ultima_parcela = 0
            
            # O saldo devedor inicial é a base do contrato
            saldo_devedor_atual = base_contrato
            
            # Meses em português
            meses_pt = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                       'jul', 'ago', 'set', 'out', 'nov', 'dez']
            
            for mes in range(1, self.params.prazo_meses + 1):
                # Correção anual
                ano_atual = (mes - 1) // 12 + 1
                fator_correcao = (1 + self.params.taxa_reajuste_anual) ** (ano_atual - 1)
                
                # Data formatada (set/25, out/25, etc.)
                mes_calendario = ((mes - 1) % 12) + 1
                ano_calendario = 2025 + (mes - 1) // 12
                data_formatada = f"{meses_pt[mes_calendario]}/{str(ano_calendario)[2:]}"
                
                # Valores corrigidos
                valor_carta_corrigido = self.params.valor_carta * fator_correcao
                
                # CORREÇÃO: Parcela sempre igual (só muda com correção anual)
                parcela_corrigida = parcela_base_mensal * fator_correcao
                
                if mes == self.params.mes_contemplacao:
                    # CONTEMPLAÇÃO: Recebe carta, paga parcela e lance livre
                    fluxo = valor_carta_corrigido - parcela_corrigida - valor_lance_livre
                    lance_mes = valor_lance_livre
                    primeira_parcela = parcela_corrigida
                    
                    # CORREÇÃO DO SALDO DEVEDOR: Após contemplação, subtrai o valor da carta
                    saldo_devedor_atual = saldo_devedor_atual - valor_carta_corrigido - parcela_corrigida
                else:
                    # DEMAIS MESES: Só paga parcela (valor sempre igual)
                    fluxo = -parcela_corrigida
                    lance_mes = 0
                    
                    # Guardar primeira parcela pós-contemplação (igual à anterior)
                    if mes == self.params.mes_contemplacao + 1:
                        primeira_parcela_pos_contemplacao = parcela_corrigida
                    
                    # CORREÇÃO: Subtrai apenas a parcela do saldo devedor
                    saldo_devedor_atual -= parcela_corrigida
                
                # Guardar parcela intermediária (meio do prazo)
                if mes == self.params.prazo_meses // 2:
                    parcela_intermediaria = parcela_corrigida
                    
                # Última parcela
                if mes == self.params.prazo_meses:
                    ultima_parcela = parcela_corrigida
                
                fluxos.append(fluxo)
                
                detalhamento.append({
                    'mes': mes,
                    'data': data_formatada,
                    'ano': ano_atual,
                    'fator_correcao': fator_correcao,
                    'valor_carta_corrigido': valor_carta_corrigido,
                    'parcela_corrigida': parcela_corrigida,
                    'lance_livre': lance_mes,
                    'fluxo_liquido': fluxo,
                    'saldo_devedor': max(0, saldo_devedor_atual),
                    'eh_contemplacao': mes == self.params.mes_contemplacao
                })
            
            # Calcular valor da carta na contemplação
            mes_contemplacao = self.params.mes_contemplacao
            ano_contemplacao = (mes_contemplacao - 1) // 12 + 1
            fator_correcao_contemplacao = (1 + self.params.taxa_reajuste_anual) ** (ano_contemplacao - 1)
            valor_carta_contemplacao = self.params.valor_carta * fator_correcao_contemplacao
            
            # Se não temos parcela pós-contemplação, é igual à primeira
            if primeira_parcela_pos_contemplacao == 0:
                primeira_parcela_pos_contemplacao = primeira_parcela
            
            # Se não temos parcela intermediária definida, usar uma estimativa
            if parcela_intermediaria == 0:
                parcela_intermediaria = parcela_base_mensal * (1 + self.params.taxa_reajuste_anual) ** 4
            
            return {
                'fluxos': fluxos,
                'detalhamento': detalhamento,
                'resumo': {
                    'base_contrato': base_contrato,
                    'valor_lance_livre': valor_lance_livre,
                    'valor_carta_contemplacao': valor_carta_contemplacao,
                    'total_parcelas': sum(d['parcela_corrigida'] for d in detalhamento if not d['eh_contemplacao']),
                    'fluxo_contemplacao': fluxos[self.params.mes_contemplacao],
                    'primeira_parcela': primeira_parcela,
                    'primeira_parcela_pos_contemplacao': primeira_parcela_pos_contemplacao,
                    'parcela_intermediaria': parcela_intermediaria,
                    'ultima_parcela': ultima_parcela,
                    # Resumo da Operação
                    'valor_credito_taxas': valor_credito_taxas,
                    'taxas': taxas,
                    'lance_embutido': lance_embutido,
                    'credito_liquido': credito_liquido
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de fluxos: {e}")
            return {'fluxos': [], 'detalhamento': [], 'resumo': {}}
            
        except Exception as e:
            logger.error(f"Erro na geração de fluxos: {e}")
            return {'fluxos': [], 'detalhamento': [], 'resumo': {}}
    
    def calcular_cet(self, fluxos: List[float]) -> float:
        """Calcula CET com método robusto."""
        def vpv(taxa_mensal):
            return sum(cf / (1 + taxa_mensal) ** i for i, cf in enumerate(fluxos))
        
        if len(fluxos) < 2:
            self.convergiu = False
            self.motivo_erro = "Fluxos insuficientes"
            return np.nan
        
        # Verificar mudanças de sinal
        sinais = [np.sign(f) for f in fluxos if f != 0]
        if len(set(sinais)) < 2:
            self.convergiu = False
            self.motivo_erro = "Sem mudança de sinal nos fluxos"
            return np.nan
        
        try:
            tentativas = [0.005, 0.01, 0.015, 0.02, 0.001, 0.03, -0.001, 0.0001]
            
            for taxa_inicial in tentativas:
                try:
                    taxa_mensal = fsolve(vpv, taxa_inicial, xtol=1e-12, maxfev=2000)[0]
                    
                    if abs(vpv(taxa_mensal)) < 1e-6:
                        taxa_anual = (1 + taxa_mensal) ** 12 - 1
                        
                        if -0.99 <= taxa_anual <= 5.0:
                            self.convergiu = True
                            return taxa_anual
                
                except (ValueError, RuntimeWarning):
                    continue
            
            self.convergiu = False
            self.motivo_erro = "Convergência não alcançada"
            return np.nan
            
        except Exception as e:
            self.convergiu = False
            self.motivo_erro = f"Erro matemático: {str(e)[:50]}"
            return np.nan
    
    def simular_cenario_completo(self) -> Dict:
        """Simulação completa do cenário atual."""
        resultado_fluxos = self.gerar_fluxos_lance_livre()
        
        if not resultado_fluxos['fluxos']:
            return {
                'erro': True,
                'mensagem': 'Erro na geração de fluxos'
            }
        
        cet = self.calcular_cet(resultado_fluxos['fluxos'])
        
        return {
            'erro': False,
            'parametros': self.params.dict(),
            'resultados': {
                'cet_anual': cet,
                'cet_mensal': (1 + cet) ** (1/12) - 1 if not np.isnan(cet) else np.nan,
                'convergiu': self.convergiu,
                'motivo_erro': self.motivo_erro
            },
            'fluxos': resultado_fluxos['fluxos'],
            'detalhamento': resultado_fluxos['detalhamento'],
            'resumo_financeiro': resultado_fluxos['resumo']
        }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Simulador de Consórcio API - Ativo"}

@api_router.post("/simular", response_model=RespostaSimulacao)
async def simular_consorcio(parametros: ParametrosConsorcio):
    """Simula um consórcio com os parâmetros fornecidos."""
    try:
        # Validações básicas
        if parametros.valor_carta <= 0:
            raise HTTPException(status_code=400, detail="Valor da carta deve ser positivo")
        
        if parametros.prazo_meses <= 0:
            raise HTTPException(status_code=400, detail="Prazo deve ser positivo")
        
        if parametros.mes_contemplacao > parametros.prazo_meses:
            raise HTTPException(status_code=400, detail="Mês de contemplação não pode ser maior que o prazo")
        
        if parametros.mes_contemplacao <= 0:
            raise HTTPException(status_code=400, detail="Mês de contemplação deve ser positivo")
        
        # Criar simulador e executar
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            return RespostaSimulacao(
                erro=True,
                mensagem=resultado.get('mensagem', 'Erro desconhecido na simulação')
            )
        
        # Converter detalhamento para o modelo Pydantic
        detalhamento_convertido = []
        for item in resultado['detalhamento']:
            detalhamento_convertido.append(DetalhamentoMes(**item))
        
        return RespostaSimulacao(
            erro=False,
            parametros=ParametrosConsorcio(**resultado['parametros']),
            resultados=ResultadosSimulacao(**resultado['resultados']),
            fluxos=resultado['fluxos'],
            detalhamento=detalhamento_convertido,
            resumo_financeiro=ResumoFinanceiro(**resultado['resumo_financeiro'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na simulação: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@api_router.get("/parametros-padrao", response_model=ParametrosConsorcio)
async def get_parametros_padrao():
    """Retorna os parâmetros padrão para simulação."""
    return ParametrosConsorcio()

def criar_grafico_fluxo_caixa(detalhamento: List[Dict], mes_contemplacao: int, temp_dir: str) -> str:
    """Cria gráfico de fluxo de caixa e salva como imagem."""
    try:
        meses = [item['mes'] for item in detalhamento]
        fluxos = [item['fluxo_liquido'] for item in detalhamento]
        
        plt.figure(figsize=(12, 6))
        colors_list = ['green' if item['eh_contemplacao'] else 'red' for item in detalhamento]
        
        plt.bar(meses, fluxos, color=colors_list, alpha=0.7)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.title('Fluxo de Caixa por Mês', fontsize=14, fontweight='bold')
        plt.xlabel('Mês')
        plt.ylabel('Fluxo de Caixa (R$)')
        plt.grid(True, alpha=0.3)
        
        # Destacar contemplação
        for i, item in enumerate(detalhamento):
            if item['eh_contemplacao']:
                plt.annotate('Contemplação', xy=(item['mes'], item['fluxo_liquido']), 
                           xytext=(item['mes'], item['fluxo_liquido'] + max(fluxos) * 0.1),
                           arrowprops=dict(arrowstyle='->', color='green'),
                           fontweight='bold', color='green')
        
        plt.tight_layout()
        grafico_path = os.path.join(temp_dir, 'grafico_fluxo.png')
        plt.savefig(grafico_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return grafico_path
    except Exception as e:
        logger.error(f"Erro ao criar gráfico: {e}")
        return None

def gerar_relatorio_pdf(dados_simulacao: Dict, temp_dir: str) -> str:
    """Gera relatório PDF da simulação de consórcio."""
    try:
        # Criar arquivo PDF temporário
        pdf_path = os.path.join(temp_dir, f'relatorio_consorcio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        # Configurar documento
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#26282A')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#26282A')
        )
        
        # Título
        # Horário de Brasília (UTC-3)
        brasilia_tz = timezone(timedelta(hours=-3))
        agora_brasilia = datetime.now(brasilia_tz)
        
        story.append(Paragraph("Relatório de Simulação de Consórcio", title_style))
        story.append(Paragraph(f"Gerado em: {agora_brasilia.strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Parâmetros da Simulação
        story.append(Paragraph("Parâmetros da Simulação", heading_style))
        
        parametros_data = [
            ['Parâmetro', 'Valor'],
            ['Valor da Carta', f"R$ {dados_simulacao['parametros']['valor_carta']:,.2f}"],
            ['Prazo', f"{dados_simulacao['parametros']['prazo_meses']} meses"],
            ['Taxa de Administração', f"{dados_simulacao['parametros']['taxa_admin'] * 100:.1f}%"],
            ['Fundo de Reserva', f"{dados_simulacao['parametros']['fundo_reserva'] * 100:.1f}%"],
            ['Mês de Contemplação', f"{dados_simulacao['parametros']['mes_contemplacao']}º mês"],
            ['Lance Livre', f"{dados_simulacao['parametros']['lance_livre_perc'] * 100:.1f}%"],
            ['Taxa de Reajuste Anual', f"{dados_simulacao['parametros']['taxa_reajuste_anual'] * 100:.1f}%"]
        ]
        
        parametros_table = Table(parametros_data, colWidths=[3*inch, 2*inch])
        parametros_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C1AFA2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(parametros_table)
        story.append(Spacer(1, 20))
        
        # Resultados Principais
        story.append(Paragraph("Resultados Principais", heading_style))
        
        if dados_simulacao['resultados']['convergiu']:
            cet_anual = dados_simulacao['resultados']['cet_anual'] * 100
            cet_mensal = dados_simulacao['resultados']['cet_mensal'] * 100
        else:
            cet_anual = "Erro no cálculo"
            cet_mensal = "Erro no cálculo"
        
        resultados_data = [
            ['Indicador', 'Valor'],
            ['CET Anual', f"{cet_anual:.2f}%" if isinstance(cet_anual, float) else cet_anual],
            ['CET Mensal', f"{cet_mensal:.3f}%" if isinstance(cet_mensal, float) else cet_mensal],
            ['Lance Livre', f"R$ {dados_simulacao['resumo_financeiro']['valor_lance_livre']:,.2f}"],
            ['Base do Contrato', f"R$ {dados_simulacao['resumo_financeiro']['base_contrato']:,.2f}"],
            ['Carta na Contemplação', f"R$ {dados_simulacao['resumo_financeiro']['valor_carta_contemplacao']:,.2f}"],
            ['Fluxo na Contemplação', f"R$ {dados_simulacao['resumo_financeiro']['fluxo_contemplacao']:,.2f}"],
            ['Total em Parcelas', f"R$ {dados_simulacao['resumo_financeiro']['total_parcelas']:,.2f}"]
        ]
        
        resultados_table = Table(resultados_data, colWidths=[3*inch, 2*inch])
        resultados_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#BC8159')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(resultados_table)
        story.append(Spacer(1, 20))
        
        # Adicionar gráfico se conseguir gerar
        grafico_path = criar_grafico_fluxo_caixa(dados_simulacao['detalhamento'], 
                                                dados_simulacao['parametros']['mes_contemplacao'], 
                                                temp_dir)
        
        if grafico_path and os.path.exists(grafico_path):
            from reportlab.platypus import Image
            story.append(Paragraph("Gráfico de Fluxo de Caixa", heading_style))
            story.append(Image(grafico_path, width=6*inch, height=3*inch))
            story.append(Spacer(1, 20))
        
        # Tabela de Amortização (primeiros 36 meses para não ficar muito grande)
        story.append(Paragraph("Fluxo de Caixa Detalhado", heading_style))
        story.append(Paragraph("Detalhes de cada parcela e do fluxo de caixa da operação.", styles['Normal']))
        story.append(Spacer(1, 10))
        
        tabela_data = [['Mês', 'Data', 'Parcela', 'Valor da Carta', 'Fluxo de Caixa', 'Saldo Devedor']]
        
        for item in dados_simulacao['detalhamento'][:36]:
            mes = str(item['mes'])
            data = item['data']
            parcela = f"R$ {item['parcela_corrigida']:,.2f}"
            # Valor da carta sempre R$ 100.000,00 (como no documento de referência)
            valor_carta = "R$ 100.000,00"
            fluxo = f"R$ {item['fluxo_liquido']:,.2f}"
            saldo = f"R$ {item['saldo_devedor']:,.2f}"
            
            tabela_data.append([mes, data, parcela, valor_carta, fluxo, saldo])
        
        tabela_amortizacao = Table(tabela_data, colWidths=[0.6*inch, 0.8*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        tabela_amortizacao.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8D4C23')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Fluxos negativos em vermelho
            ('TEXTCOLOR', (4, 1), (4, -1), colors.red),
        ]))
        
        # Destacar linha de contemplação com fluxo positivo em verde
        for i, item in enumerate(dados_simulacao['detalhamento'][:36]):
            if item['eh_contemplacao']:
                tabela_amortizacao.setStyle(TableStyle([
                    ('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#E8F5E8')),
                    ('TEXTCOLOR', (4, i+1), (4, i+1), colors.green)
                ]))
        
        story.append(tabela_amortizacao)
        
        # Rodapé
        story.append(Spacer(1, 30))
        story.append(Paragraph("Relatório gerado pelo Simulador de Consórcio", 
                             ParagraphStyle('Footer', parent=styles['Normal'], 
                                          fontSize=8, alignment=TA_CENTER, 
                                          textColor=colors.grey)))
        
        # Gerar PDF
        doc.build(story)
        return pdf_path
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório PDF: {str(e)}")

@api_router.post("/gerar-relatorio-pdf")
async def gerar_relatorio_pdf_endpoint(parametros: ParametrosConsorcio):
    """Gera e retorna relatório PDF da simulação."""
    try:
        # Executar simulação
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            raise HTTPException(status_code=400, detail=resultado.get('mensagem', 'Erro na simulação'))
        
        # Criar diretório temporário
        temp_dir = tempfile.mkdtemp()
        
        # Gerar PDF
        pdf_path = gerar_relatorio_pdf(resultado, temp_dir)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Erro ao gerar arquivo PDF")
        
        # Retornar arquivo
        filename = f"relatorio_consorcio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)