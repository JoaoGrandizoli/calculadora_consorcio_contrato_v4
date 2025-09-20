import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Separator } from './components/ui/separator';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { AlertCircle, Calculator, TrendingUp, FileText, PieChart, Download } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import './App.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [parametros, setParametros] = useState({
    valor_carta: 100000,
    prazo_meses: 120,
    taxa_admin: 0.21,
    fundo_reserva: 0.03,
    mes_contemplacao: 1,
    lance_livre_perc: 0.10,
    taxa_reajuste_anual: 0.05
  });

  const [resultados, setResultados] = useState(null);
  const [probabilidades, setProbabilidades] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [loadingProb, setLoadingProb] = useState(false);
  const [erro, setErro] = useState(null);
  const [parametrosProb, setParametrosProb] = useState({
    num_participantes: 430,
    contemplados_por_mes: 2
  });

  // Carregar parâmetros padrão ao inicializar
  useEffect(() => {
    const carregarParametrosPadrao = async () => {
      try {
        const response = await axios.get(`${API}/parametros-padrao`);
        setParametros(response.data);
      } catch (error) {
        console.error('Erro ao carregar parâmetros padrão:', error);
      }
    };
    carregarParametrosPadrao();
  }, []);

  const handleInputChange = (field, value) => {
    setParametros(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const simularConsorcio = async () => {
    setLoading(true);
    setErro(null);
    
    try {
      const response = await axios.post(`${API}/simular`, parametros);
      
      if (response.data.erro) {
        setErro(response.data.mensagem);
        setResultados(null);
      } else {
        setResultados(response.data);
      }
    } catch (error) {
      setErro(error.response?.data?.detail || 'Erro ao simular consórcio');
      setResultados(null);
    } finally {
      setLoading(false);
    }
  };

  const formatarMoeda = (valor) => {
    return valor.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    });
  };

  const formatarPorcentagem = (valor) => {
    return (valor * 100).toFixed(2) + '%';
  };

  const downloadRelatorioPdf = async () => {
    setLoadingPdf(true);
    
    try {
      const response = await axios.post(`${API}/gerar-relatorio-pdf`, parametros, {
        responseType: 'blob'
      });
      
      // Criar URL do blob e fazer download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Nome do arquivo com timestamp
      const timestamp = new Date().toISOString().slice(0, 16).replace(/[:-]/g, '');
      link.setAttribute('download', `relatorio_consorcio_${timestamp}.pdf`);
      
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Erro ao baixar relatório:', error);
      setErro('Erro ao gerar relatório PDF. Tente novamente.');
    } finally {
      setLoadingPdf(false);
    }
  };

  const calcularProbabilidades = async () => {
    setLoadingProb(true);
    setErro(null);
    
    try {
      const response = await axios.post(`${API}/calcular-probabilidades`, parametrosProb);
      
      if (response.data.erro) {
        setErro(response.data.mensagem);
        setProbabilidades(null);
      } else {
        setProbabilidades(response.data);
      }
    } catch (error) {
      setErro(error.response?.data?.detail || 'Erro ao calcular probabilidades');
      setProbabilidades(null);
    } finally {
      setLoadingProb(false);
    }
  };

  return (
    <div className="min-h-screen bg-light">
      {/* Header */}
      <div className="bg-primary-accent text-light border-b border-moonstone">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center gap-3">
            <Calculator className="h-8 w-8 text-accent-warm" />
            <div>
              <h1 className="text-2xl font-bold">Simulador de Consórcio</h1>
              <p className="text-neutral-light opacity-90">Análise completa de lance livre e fluxos de caixa</p>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 md:px-6 py-4 md:py-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 md:gap-8">
          {/* Painel de Parâmetros */}
          <div className="lg:col-span-2">
            <Card className="border-moonstone shadow-sm">
              <CardHeader className="bg-neutral-light border-b border-moonstone">
                <CardTitle className="text-primary-accent flex items-center gap-2 text-lg md:text-xl">
                  <TrendingUp className="h-5 w-5" />
                  Parâmetros da Simulação
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 md:p-6 space-y-4 md:space-y-6">
                {/* Valor da Carta */}
                <div className="space-y-2">
                  <Label htmlFor="valor_carta" className="text-primary-accent font-medium text-sm md:text-base">
                    Valor da Carta (R$)
                  </Label>
                  <Input
                    id="valor_carta"
                    type="number"
                    value={parametros.valor_carta}
                    onChange={(e) => handleInputChange('valor_carta', parseFloat(e.target.value))}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                {/* Prazo */}
                <div className="space-y-2">
                  <Label htmlFor="prazo_meses" className="text-primary-accent font-medium text-sm md:text-base">
                    Prazo (meses)
                  </Label>
                  <Input
                    id="prazo_meses"
                    type="number"
                    value={parametros.prazo_meses}
                    onChange={(e) => handleInputChange('prazo_meses', parseInt(e.target.value))}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                {/* Taxa Admin */}
                <div className="space-y-2">
                  <Label htmlFor="taxa_admin" className="text-primary-accent font-medium text-sm md:text-base">
                    Taxa de Administração (%)
                  </Label>
                  <Input
                    id="taxa_admin"
                    type="number"
                    step="0.01"
                    value={parametros.taxa_admin * 100}
                    onChange={(e) => handleInputChange('taxa_admin', parseFloat(e.target.value) / 100)}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                {/* Fundo de Reserva */}
                <div className="space-y-2">
                  <Label htmlFor="fundo_reserva" className="text-primary-accent font-medium text-sm md:text-base">
                    Fundo de Reserva (%)
                  </Label>
                  <Input
                    id="fundo_reserva"
                    type="number"
                    step="0.01"
                    value={parametros.fundo_reserva * 100}
                    onChange={(e) => handleInputChange('fundo_reserva', parseFloat(e.target.value) / 100)}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                {/* Mês de Contemplação */}
                <div className="space-y-2">
                  <Label htmlFor="mes_contemplacao" className="text-primary-accent font-medium text-sm md:text-base">
                    Mês de Contemplação
                  </Label>
                  <Input
                    id="mes_contemplacao"
                    type="number"
                    value={parametros.mes_contemplacao}
                    onChange={(e) => handleInputChange('mes_contemplacao', parseInt(e.target.value))}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                {/* Lance Livre */}
                <div className="space-y-2">
                  <Label htmlFor="lance_livre_perc" className="text-primary-accent font-medium text-sm md:text-base">
                    Lance Livre (%)
                  </Label>
                  <Input
                    id="lance_livre_perc"
                    type="number"
                    step="0.01"
                    value={parametros.lance_livre_perc * 100}
                    onChange={(e) => handleInputChange('lance_livre_perc', parseFloat(e.target.value) / 100)}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                {/* Taxa de Reajuste */}
                <div className="space-y-2">
                  <Label htmlFor="taxa_reajuste_anual" className="text-primary-accent font-medium text-sm md:text-base">
                    Taxa de Reajuste Anual (%)
                  </Label>
                  <Input
                    id="taxa_reajuste_anual"
                    type="number"
                    step="0.01"
                    value={parametros.taxa_reajuste_anual * 100}
                    onChange={(e) => handleInputChange('taxa_reajuste_anual', parseFloat(e.target.value) / 100)}
                    className="border-moonstone focus:border-accent-warm text-base"
                  />
                </div>

                <Separator className="bg-moonstone" />

                <div className="space-y-3">
                  <Button 
                    onClick={simularConsorcio}
                    disabled={loading}
                    className="w-full bg-accent-warm hover:bg-accent-dark text-light font-medium py-3 text-base"
                  >
                    {loading ? 'Simulando...' : 'Simular Consórcio'}
                  </Button>
                  
                  {resultados && !resultados.erro && (
                    <Button 
                      onClick={downloadRelatorioPdf}
                      disabled={loadingPdf}
                      variant="outline"
                      className="w-full border-accent-warm text-accent-dark hover:bg-accent-warm hover:text-light font-medium py-3 text-base"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      {loadingPdf ? 'Gerando PDF...' : 'Baixar Relatório PDF'}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Painel de Resultados */}
          <div className="lg:col-span-3">
            {erro && (
              <Card className="border-red-200 bg-red-50 mb-4 md:mb-6">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-red-700">
                    <AlertCircle className="h-5 w-5" />
                    <span className="font-medium text-sm md:text-base">Erro: {erro}</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {resultados && !resultados.erro && (
              <div className="space-y-4 md:space-y-6">
                {/* Cards de Resumo */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
                  <Card className="border-moonstone">
                    <CardContent className="p-4 md:p-6">
                      <div className="flex items-center gap-3">
                        <div className="p-2 md:p-3 bg-accent-warm rounded-lg">
                          <PieChart className="h-4 w-4 md:h-6 md:w-6 text-light" />
                        </div>
                        <div>
                          <p className="text-xs md:text-sm text-neutral-mid">CET Anual</p>
                          <p className="text-lg md:text-2xl font-bold text-primary-accent">
                            {resultados.resultados.convergiu ? 
                              formatarPorcentagem(resultados.resultados.cet_anual) : 
                              'Erro no cálculo'
                            }
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="border-moonstone">
                    <CardContent className="p-4 md:p-6">
                      <div className="flex items-center gap-3">
                        <div className="p-2 md:p-3 bg-accent-medium rounded-lg">
                          <TrendingUp className="h-4 w-4 md:h-6 md:w-6 text-light" />
                        </div>
                        <div>
                          <p className="text-xs md:text-sm text-neutral-mid">Lance Livre</p>
                          <p className="text-lg md:text-2xl font-bold text-primary-accent">
                            {formatarMoeda(resultados.resumo_financeiro.valor_lance_livre)}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="border-moonstone">
                    <CardContent className="p-4 md:p-6">
                      <div className="flex items-center gap-3">
                        <div className="p-2 md:p-3 bg-accent-dark rounded-lg">
                          <Calculator className="h-4 w-4 md:h-6 md:w-6 text-light" />
                        </div>
                        <div>
                          <p className="text-xs md:text-sm text-neutral-mid">Valor da Carta</p>
                          <p className="text-lg md:text-2xl font-bold text-primary-accent">
                            {formatarMoeda(resultados.resumo_financeiro.valor_carta_contemplacao)}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="border-moonstone">
                    <CardContent className="p-4 md:p-6">
                      <div className="flex items-center gap-3">
                        <div className="p-2 md:p-3 bg-accent-light rounded-lg">
                          <FileText className="h-4 w-4 md:h-6 md:w-6 text-light" />
                        </div>
                        <div>
                          <p className="text-xs md:text-sm text-neutral-mid">Fluxo Líquido Contemplação</p>
                          <p className="text-lg md:text-2xl font-bold text-green-600">
                            {formatarMoeda(resultados.resumo_financeiro.fluxo_contemplacao)}
                          </p>
                          <p className="text-xs text-neutral-mid">Carta - Parcela - Lance</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Detalhamento */}
                <Card className="border-moonstone">
                  <CardHeader className="bg-neutral-light border-b border-moonstone">
                    <CardTitle className="text-primary-accent text-lg md:text-xl">Análise Completa</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 md:p-6">
                    <Tabs defaultValue="resumo" className="w-full">
                      <TabsList className="grid w-full grid-cols-3 bg-neutral-light">
                        <TabsTrigger value="resumo" className="data-[state=active]:bg-accent-warm data-[state=active]:text-light text-sm md:text-base">
                          Resumo Financeiro
                        </TabsTrigger>
                        <TabsTrigger value="detalhes" className="data-[state=active]:bg-accent-warm data-[state=active]:text-light text-sm md:text-base">
                          Fluxo de Caixa
                        </TabsTrigger>
                        <TabsTrigger value="probabilidades" className="data-[state=active]:bg-accent-warm data-[state=active]:text-light text-sm md:text-base">
                          Probabilidades
                        </TabsTrigger>
                      </TabsList>
                      
                      <TabsContent value="resumo" className="space-y-4">
                        {/* Resumo da Contemplação */}
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                          <h4 className="text-green-800 font-semibold mb-3">💰 Resumo da Contemplação (Mês {parametros.mes_contemplacao})</h4>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <div className="text-center">
                              <p className="text-green-600 font-mono text-lg">+{formatarMoeda(resultados.resumo_financeiro.valor_carta_contemplacao)}</p>
                              <p className="text-green-700">Recebe a Carta</p>
                            </div>
                            <div className="text-center">
                              <p className="text-red-600 font-mono text-lg">-{formatarMoeda(resultados.resumo_financeiro.primeira_parcela)}</p>
                              <p className="text-red-700">Paga Parcela</p>
                            </div>
                            <div className="text-center">
                              <p className="text-red-600 font-mono text-lg">-{formatarMoeda(resultados.resumo_financeiro.valor_lance_livre)}</p>
                              <p className="text-red-700">Paga Lance Livre</p>
                            </div>
                          </div>
                          <div className="text-center mt-3 pt-3 border-t border-green-300">
                            <p className="text-green-800 font-semibold">Fluxo Líquido: <span className="font-mono text-lg text-green-600">{formatarMoeda(resultados.resumo_financeiro.fluxo_contemplacao)}</span></p>
                          </div>
                        </div>

                        {/* Probabilidades do Mês Escolhido */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                          <h4 className="text-blue-800 font-semibold mb-3">🎲 Probabilidades para o Mês {parametros.mes_contemplacao}</h4>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <div className="text-center">
                              <p className="text-blue-600 font-mono text-lg">{(resultados.resumo_financeiro.prob_contemplacao_no_mes * 100).toFixed(3)}%</p>
                              <p className="text-blue-700">Prob. no Mês {parametros.mes_contemplacao}</p>
                              <p className="text-xs text-blue-600">
                                {parametros.lance_livre_perc > 0 ? '2' : '1'}/{resultados.resumo_financeiro.participantes_restantes_mes} participantes
                              </p>
                            </div>
                            <div className="text-center">
                              <p className="text-blue-600 font-mono text-lg">{(resultados.resumo_financeiro.prob_contemplacao_ate_mes * 100).toFixed(2)}%</p>
                              <p className="text-blue-700">Prob. até o Mês {parametros.mes_contemplacao}</p>
                              <p className="text-xs text-blue-600">Probabilidade Acumulada</p>
                            </div>
                            <div className="text-center">
                              <p className="text-blue-600 font-mono text-lg">{resultados.resumo_financeiro.participantes_restantes_mes}</p>
                              <p className="text-blue-700">Participantes Restantes</p>
                              <p className="text-xs text-blue-600">No início do mês</p>
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-3">
                            <div className="flex justify-between items-center">
                              <span className="text-neutral-mid text-sm md:text-base">Base do Contrato:</span>
                              <Badge variant="outline" className="font-mono text-xs md:text-sm">
                                {formatarMoeda(resultados.resumo_financeiro.base_contrato)}
                              </Badge>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-neutral-mid text-sm md:text-base">Carta na Contemplação:</span>
                              <Badge variant="outline" className="font-mono text-xs md:text-sm">
                                {formatarMoeda(resultados.resumo_financeiro.valor_carta_contemplacao)}
                              </Badge>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-neutral-mid text-sm md:text-base">1ª Parcela (Início):</span>
                              <Badge variant="outline" className="font-mono text-xs md:text-sm">
                                {formatarMoeda(resultados.resumo_financeiro.primeira_parcela)}
                              </Badge>
                            </div>
                          </div>
                          <div className="space-y-3">
                            {resultados.resultados.convergiu && (
                              <>
                                <div className="flex justify-between items-center">
                                  <span className="text-neutral-mid text-sm md:text-base">CET Mensal:</span>
                                  <Badge variant="outline" className="font-mono text-xs md:text-sm">
                                    {formatarPorcentagem(resultados.resultados.cet_mensal)}
                                  </Badge>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-neutral-mid text-sm md:text-base">1ª Parcela Pós-Contemplação:</span>
                                  <Badge variant="outline" className="font-mono text-xs md:text-sm">
                                    {formatarMoeda(resultados.resumo_financeiro.primeira_parcela_pos_contemplacao)}
                                  </Badge>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-neutral-mid text-sm md:text-base">Última Parcela:</span>
                                  <Badge variant="outline" className="font-mono text-xs md:text-sm">
                                    {formatarMoeda(resultados.resumo_financeiro.ultima_parcela)}
                                  </Badge>
                                </div>
                              </>
                            )}
                            <div className="flex justify-between items-center">
                              <span className="text-neutral-mid text-sm md:text-base">Status:</span>
                              <Badge className="bg-green-100 text-green-800 border-green-200 text-xs md:text-sm">
                                Cálculo OK
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </TabsContent>

                      <TabsContent value="detalhes">
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-moonstone bg-neutral-light">
                                <th className="p-2 md:p-3 text-left text-primary-accent text-xs md:text-sm">Mês</th>
                                <th className="p-2 md:p-3 text-left text-primary-accent text-xs md:text-sm">Data</th>
                                <th className="p-2 md:p-3 text-right text-primary-accent text-xs md:text-sm">Parcela</th>
                                <th className="p-2 md:p-3 text-right text-primary-accent text-xs md:text-sm">Valor da Carta</th>
                                <th className="p-2 md:p-3 text-right text-primary-accent text-xs md:text-sm">Fluxo de Caixa</th>
                                <th className="p-2 md:p-3 text-right text-primary-accent text-xs md:text-sm">Saldo Devedor</th>
                                <th className="p-2 md:p-3 text-center text-primary-accent text-xs md:text-sm">Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {resultados.detalhamento.slice(0, 24).map((item, index) => (
                                <tr key={index} className={`border-b border-gray-100 ${item.eh_contemplacao ? 'bg-green-50' : ''}`}>
                                  <td className="p-2 md:p-3 text-primary-accent font-medium text-xs md:text-sm">{item.mes}</td>
                                  <td className="p-2 md:p-3 text-primary-accent text-xs md:text-sm">{item.data}</td>
                                  <td className="p-2 md:p-3 text-right font-mono text-neutral-dark text-xs md:text-sm">
                                    {formatarMoeda(item.parcela_corrigida)}
                                  </td>
                                  <td className="p-2 md:p-3 text-right font-mono text-neutral-dark text-xs md:text-sm">
                                    R$ 100.000,00
                                  </td>
                                  <td className={`p-2 md:p-3 text-right font-mono text-xs md:text-sm ${item.fluxo_liquido > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {formatarMoeda(item.fluxo_liquido)}
                                  </td>
                                  <td className="p-2 md:p-3 text-right font-mono text-neutral-dark text-xs md:text-sm">
                                    {formatarMoeda(item.saldo_devedor)}
                                  </td>
                                  <td className="p-2 md:p-3 text-center">
                                    {item.eh_contemplacao && (
                                      <Badge className="bg-green-100 text-green-800 border-green-200 text-xs">
                                        Contemplação
                                      </Badge>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </TabsContent>

                      <TabsContent value="probabilidades" className="space-y-4">
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                          <h4 className="text-blue-800 font-semibold mb-3">🎲 Configurar Análise de Probabilidades</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <Label className="text-sm font-medium text-blue-700">Participantes do Grupo</Label>
                              <Input
                                type="number"
                                value={parametrosProb.num_participantes}
                                onChange={(e) => setParametrosProb(prev => ({...prev, num_participantes: parseInt(e.target.value)}))}
                                className="mt-1"
                              />
                            </div>
                            <div>
                              <Label className="text-sm font-medium text-blue-700">Contemplados por Mês</Label>
                              <Input
                                type="number"
                                value={parametrosProb.contemplados_por_mes}
                                onChange={(e) => setParametrosProb(prev => ({...prev, contemplados_por_mes: parseInt(e.target.value)}))}
                                className="mt-1"
                              />
                            </div>
                          </div>
                          <Button 
                            onClick={calcularProbabilidades}
                            disabled={loadingProb}
                            className="mt-3 bg-blue-600 hover:bg-blue-700 text-white"
                          >
                            {loadingProb ? 'Calculando...' : 'Calcular Probabilidades'}
                          </Button>
                        </div>

                        {probabilidades && !probabilidades.erro && (
                          <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <Card className="border-blue-200">
                                <CardContent className="p-4 text-center">
                                  <p className="text-sm text-blue-600">Tempo Esperado</p>
                                  <p className="text-2xl font-bold text-blue-800">
                                    {probabilidades.com_lance.esperanca_meses.toFixed(1)} meses
                                  </p>
                                </CardContent>
                              </Card>
                              <Card className="border-blue-200">
                                <CardContent className="p-4 text-center">
                                  <p className="text-sm text-blue-600">Mediana</p>
                                  <p className="text-2xl font-bold text-blue-800">
                                    {probabilidades.com_lance.mediana_mes} meses
                                  </p>
                                </CardContent>
                              </Card>
                              <Card className="border-blue-200">
                                <CardContent className="p-4 text-center">
                                  <p className="text-sm text-blue-600">Intervalo 80%</p>
                                  <p className="text-lg font-bold text-blue-800">
                                    {probabilidades.com_lance.p10_mes} - {probabilidades.com_lance.p90_mes} meses
                                  </p>
                                </CardContent>
                              </Card>
                            </div>

                            {/* Gráfico de Probabilidade Acumulada */}
                            <Card className="border-gray-200">
                              <CardHeader>
                                <CardTitle className="text-lg">📈 Probabilidade Acumulada de Contemplação</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="h-80">
                                  <Line 
                                    data={{
                                      labels: probabilidades.com_lance.meses.slice(0, 60), // Primeiros 60 meses
                                      datasets: [
                                        {
                                          label: 'Com Lance Livre',
                                          data: probabilidades.com_lance.probabilidade_acumulada.slice(0, 60).map(p => p * 100),
                                          borderColor: '#BC8159',
                                          backgroundColor: 'rgba(188, 129, 89, 0.1)',
                                          tension: 0.4,
                                          pointRadius: 1,
                                        },
                                        {
                                          label: 'Apenas Sorteio',
                                          data: probabilidades.sem_lance.probabilidade_acumulada.slice(0, 60).map(p => p * 100),
                                          borderColor: '#8D4C23',
                                          backgroundColor: 'rgba(141, 76, 35, 0.1)',
                                          tension: 0.4,
                                          pointRadius: 1,
                                        }
                                      ]
                                    }}
                                    options={{
                                      responsive: true,
                                      maintainAspectRatio: false,
                                      plugins: {
                                        legend: {
                                          position: 'top',
                                        },
                                        title: {
                                          display: false,
                                        },
                                      },
                                      scales: {
                                        x: {
                                          display: true,
                                          title: {
                                            display: true,
                                            text: 'Mês'
                                          }
                                        },
                                        y: {
                                          display: true,
                                          title: {
                                            display: true,
                                            text: 'Probabilidade Acumulada (%)'
                                          },
                                          min: 0,
                                          max: 100
                                        }
                                      }
                                    }}
                                  />
                                </div>
                              </CardContent>
                            </Card>

                            <div className="bg-white border border-gray-200 rounded-lg p-4">
                              <h5 className="font-semibold mb-3">Probabilidade de Contemplação por Mês</h5>
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead>
                                    <tr className="border-b bg-gray-50">
                                      <th className="p-2 text-left">Mês</th>
                                      <th className="p-2 text-right">Prob. no Mês</th>
                                      <th className="p-2 text-right">Prob. Acumulada</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {probabilidades.com_lance.meses.slice(0, 12).map((mes, index) => (
                                      <tr key={mes} className="border-b">
                                        <td className="p-2 font-medium">{mes}</td>
                                        <td className="p-2 text-right font-mono">
                                          {(probabilidades.com_lance.probabilidade_mes[index] * 100).toFixed(2)}%
                                        </td>
                                        <td className="p-2 text-right font-mono">
                                          {(probabilidades.com_lance.probabilidade_acumulada[index] * 100).toFixed(2)}%
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                              {probabilidades.com_lance.meses.length > 12 && (
                                <p className="text-xs text-gray-500 mt-2">
                                  Mostrando primeiros 12 meses de {probabilidades.parametros.meses_total} total
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              </div>
            )}

            {!resultados && !erro && !loading && (
              <Card className="border-moonstone">
                <CardContent className="p-8 md:p-12 text-center">
                  <Calculator className="h-12 w-12 md:h-16 md:w-16 text-neutral-mid mx-auto mb-4" />
                  <h3 className="text-lg md:text-xl font-semibold text-primary-accent mb-2">
                    Pronto para simular
                  </h3>
                  <p className="text-neutral-mid text-sm md:text-base">
                    Configure os parâmetros à esquerda e clique em "Simular Consórcio" para ver os resultados.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;