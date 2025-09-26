import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Separator } from './components/ui/separator';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { AlertCircle, Calculator, TrendingUp, FileText, PieChart, Download, Settings } from 'lucide-react';
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
import CadastroForm from './components/CadastroForm';
import AdminPanel from './components/AdminPanel';
import ContractAnalysis from './components/ContractAnalysis';
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
  // Estado para controle de acesso
  const [hasAccess, setHasAccess] = useState(false);
  const [accessToken, setAccessToken] = useState(null);
  const [leadInfo, setLeadInfo] = useState(null);
  const [showAdmin, setShowAdmin] = useState(false);
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [adminLoginError, setAdminLoginError] = useState('');
  
  // Estado para controlar abas principais
  const [activeTab, setActiveTab] = useState('simulador');

  // 🔧 FIX CRÍTICO: Verificar acesso admin apenas por URL, não por localStorage
  // localStorage serve apenas para persistir APÓS a autenticação
  const isAdminAccess = window.location.pathname === '/admin' || 
                        window.location.hash === '#admin';

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
    lance_livre_perc: 0.10
  });
  const [mostrarDetalheProbabilidades, setMostrarDetalheProbabilidades] = useState(false);

  // Verificar acesso ao carregar a página
  useEffect(() => {
    console.log('🔧 Inicializando aplicação...');
    
    const storedToken = localStorage.getItem('access_token');
    const adminAuth = localStorage.getItem('admin_authenticated') === 'true';
    const currentUrl = window.location.href;
    
    // 🔧 NOVA LÓGICA: Capturar parâmetros do redirect do Typeform
    const urlParams = new URLSearchParams(window.location.search);
    const emailFromUrl = urlParams.get('email');
    const timestampFromUrl = urlParams.get('t');
    const submittedFlag = urlParams.get('submitted');
    
    console.log('🔧 Estado inicial:', { 
      storedToken: !!storedToken, 
      adminAuth, 
      isAdminAccess,
      currentUrl,
      emailFromUrl,
      timestampFromUrl,
      submittedFlag
    });
    
    // 🎯 PRIORIDADE 1: Se chegou do Typeform via redirect (email + timestamp na URL)
    if (emailFromUrl && timestampFromUrl && submittedFlag === 'true') {
      console.log('🎯 REDIRECT DO TYPEFORM DETECTADO!');
      console.log('📧 Email da URL:', emailFromUrl);
      console.log('⏰ Timestamp da URL:', timestampFromUrl);
      
      // Buscar lead específico por email e timestamp
      findLeadByEmailAndTimestamp(emailFromUrl, timestampFromUrl);
      return; // Não continuar com outras verificações
    }
    
    // Resto da lógica original...
    if (storedToken) {
      setAccessToken(storedToken);
      checkAccessToken(storedToken);
    }
    
    // 🔐 CORREÇÃO: Separar detecção de URL da persistência de estado
    if (isAdminAccess) {
      // Usuário está acessando URL de admin diretamente
      console.log('🔐 URL de admin detectada');
      
      if (adminAuth) {
        console.log('🔐 Admin já autenticado - ativando modo admin');
        setAdminAuthenticated(true);
        setShowAdmin(true);
        setHasAccess(true);
        localStorage.setItem('admin_mode', 'true');
      } else {
        console.log('🔐 Solicitando autenticação admin');
        setShowAdmin(true);
        setHasAccess(true);
        // NÃO definir admin_mode aqui - só após autenticação
      }
    } else {
      // Usuário NÃO está em URL de admin
      console.log('🔧 URL normal detectada');
      
      if (adminAuth && localStorage.getItem('admin_mode') === 'true') {
        // Se estava no admin e ainda tem sessão válida, manter apenas se explicitamente solicitado
        console.log('🔧 Sessão admin existente, mas fora da URL admin - limpando modo admin');
        localStorage.removeItem('admin_mode');
        setShowAdmin(false);
      }
      
      // Garantir que não está em modo admin se não é URL admin
      setShowAdmin(false);
    }
  }, [isAdminAccess]);

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

  const handleAccessGranted = (token) => {
    setAccessToken(token);
    setHasAccess(true);
    localStorage.setItem('access_token', token);
  };

  // 🔐 NOVA FUNÇÃO: Autenticação admin
  const handleAdminLogin = (password) => {
    const correctPassword = 'Joao@123'; // Senha definida
    
    if (password === correctPassword) {
      setAdminAuthenticated(true);
      setAdminLoginError('');
      localStorage.setItem('admin_authenticated', 'true');
      console.log('✅ Admin autenticado com sucesso');
      return true;
    } else {
      setAdminLoginError('Senha incorreta. Tente novamente.');
      console.log('❌ Falha na autenticação admin');
      return false;
    }
  };

  const handleAdminLogout = () => {
    setAdminAuthenticated(false);
    setShowAdmin(false);
    localStorage.removeItem('admin_authenticated');
    localStorage.removeItem('admin_mode');
    setAdminPassword('');
    setAdminLoginError('');
    console.log('🔐 Admin logout realizado');
  };

  // 🎯 NOVA FUNÇÃO: Buscar lead por email e timestamp do redirect do Typeform
  const findLeadByEmailAndTimestamp = async (email, timestamp) => {
    console.log('🔍 Buscando lead específico por email e timestamp...');
    console.log('📧 Email:', email);
    console.log('⏰ Timestamp:', timestamp);
    
    try {
      // Converter timestamp para Date para comparação
      const submissionTime = new Date(timestamp);
      const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000); // 10 minutos de janela
      
      console.log('🕒 Janela de busca:', {
        submissionTime: submissionTime.toISOString(),
        tenMinutesAgo: tenMinutesAgo.toISOString()
      });
      
      // Buscar todos os leads
      const response = await axios.get(`${API}/admin/leads`);
      const leads = response.data.leads || [];
      
      console.log(`🔍 Verificando ${leads.length} leads...`);
      
      // Buscar lead exato por email
      const matchingLeads = leads.filter(lead => {
        const leadEmail = lead.email?.toLowerCase().trim();
        const targetEmail = email.toLowerCase().trim();
        const leadCreatedAt = new Date(lead.created_at);
        
        console.log(`📋 Verificando lead: ${lead.name} - ${leadEmail} - ${leadCreatedAt.toISOString()}`);
        
        return leadEmail === targetEmail && leadCreatedAt > tenMinutesAgo;
      });
      
      console.log(`📊 Leads compatíveis encontrados: ${matchingLeads.length}`);
      
      if (matchingLeads.length > 0) {
        // Pegar o mais recente se há múltiplos
        const selectedLead = matchingLeads.sort((a, b) => 
          new Date(b.created_at) - new Date(a.created_at)
        )[0];
        
        console.log('✅ LEAD ENCONTRADO POR EMAIL+TIMESTAMP:');
        console.log('   - Nome:', selectedLead.name);
        console.log('   - Email:', selectedLead.email);
        console.log('   - Token:', selectedLead.access_token);
        console.log('   - Criado em:', selectedLead.created_at);
        
        // Salvar dados no localStorage
        localStorage.setItem('access_token', selectedLead.access_token);
        localStorage.setItem('lead_data', JSON.stringify({
          leadId: selectedLead.id,
          name: selectedLead.name,
          email: selectedLead.email,
          token: selectedLead.access_token,
          timestamp: new Date().toISOString(),
          source: 'typeform_redirect'
        }));
        
        // Limpar parâmetros da URL
        window.history.replaceState({}, document.title, window.location.pathname);
        
        // Conceder acesso
        setAccessToken(selectedLead.access_token);
        setHasAccess(true);
        setLeadInfo({
          name: selectedLead.name,
          email: selectedLead.email,
          created_at: selectedLead.created_at
        });
        
        console.log('🎯 ACESSO CONCEDIDO VIA REDIRECT DO TYPEFORM');
        
      } else {
        console.log('❌ Nenhum lead encontrado com esse email e timestamp');
        console.log('🔄 Tentando busca por lead mais recente...');
        
        // Fallback: buscar lead mais recente
        const recentLead = leads.find(lead => {
          const leadCreatedAt = new Date(lead.created_at);
          return leadCreatedAt > tenMinutesAgo && 
                 lead.access_token && 
                 !lead.name.includes('João Silva') &&
                 !lead.name.includes('Test');
        });
        
        if (recentLead) {
          console.log('✅ FALLBACK - Lead recente encontrado:', recentLead.name);
          localStorage.setItem('access_token', recentLead.access_token);
          setAccessToken(recentLead.access_token);
          setHasAccess(true);
        } else {
          console.log('❌ Nenhum lead recente encontrado - redirecionando para formulário');
          // Não fazer nada, deixar mostrar o formulário
        }
      }
      
    } catch (error) {
      console.error('❌ Erro ao buscar lead por email/timestamp:', error);
      // Em caso de erro, não fazer nada e deixar o fluxo normal
    }
  };

  const checkAccessToken = async (token) => {
    try {
      // Verificar se o token não é muito antigo (evitar tokens de teste)
      const tokenData = localStorage.getItem('lead_data');
      if (tokenData) {
        const leadData = JSON.parse(tokenData);
        const tokenAge = Date.now() - new Date(leadData.timestamp || 0).getTime();
        
        // Se token tem mais de 24 horas, considerar inválido
        if (tokenAge > 24 * 60 * 60 * 1000) {
          console.log('🕒 Token expirado (>24h), limpando...');
          localStorage.removeItem('access_token');
          localStorage.removeItem('lead_data');
          setHasAccess(false);
          return;
        }
      }
      
      // Validar token no servidor
      const response = await axios.get(`${API}/check-access/${token}`);
      if (response.data.valid) {
        // 🔧 CORREÇÃO TEMPORÁRIA: Permitir tokens fallback para debug
        // TODO: Remover após webhook do Typeform estar funcionando
        const leadName = response.data.name || '';
        if (!leadName.includes('Teste') && 
            !leadName.includes('João Silva') && 
            !leadName.includes('Test') &&
            !token.startsWith('temp-') &&
            !token.startsWith('error-')) {
          
          console.log('✅ Token válido (incluindo fallback para debug):', token);
          setHasAccess(true);
          setAccessToken(token);
          setLeadInfo({
            name: response.data.name || 'Usuario Fallback',
            created_at: response.data.created_at
          });
        } else {
          console.log('🚮 Token de teste detectado, limpando...');
          localStorage.removeItem('access_token');
          localStorage.removeItem('lead_data');
          setHasAccess(false);
        }
      } else {
        console.log('❌ Token inválido no servidor');
        localStorage.removeItem('access_token');
        localStorage.removeItem('lead_data');
        setHasAccess(false);
      }
    } catch (error) {
      console.error('Erro ao verificar token:', error);
      // Em caso de erro, limpar token para segurança
      localStorage.removeItem('access_token');
      localStorage.removeItem('lead_data');
      setHasAccess(false);
    }
  };

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
      const headers = {};
      
      // 🔧 DEBUG: Logs detalhados do estado atual
      console.log('🔍 ESTADO ATUAL ANTES DA SIMULAÇÃO:');
      console.log('   - accessToken (state):', accessToken);
      console.log('   - localStorage access_token:', localStorage.getItem('access_token'));
      console.log('   - localStorage lead_data:', localStorage.getItem('lead_data'));
      
      // 🔧 FIX DEFINITIVO: Garantir que o token seja sempre obtido
      let tokenParaUsar = accessToken;
      if (!tokenParaUsar) {
        // Fallback: tentar obter do localStorage diretamente
        tokenParaUsar = localStorage.getItem('access_token');
        if (tokenParaUsar) {
          setAccessToken(tokenParaUsar); // Sincronizar state
          console.log('🔧 Token recuperado do localStorage:', tokenParaUsar);
        }
      }
      
      if (tokenParaUsar) {
        headers.Authorization = `Bearer ${tokenParaUsar}`;
        console.log('🎯 Enviando Authorization header:', `Bearer ${tokenParaUsar.substring(0, 8)}...`);
        console.log('🎯 Token completo para debug:', tokenParaUsar);
      } else {
        console.warn('⚠️ AVISO: Nenhum access_token disponível para a simulação');
      }
      
      console.log('📡 Headers da requisição:', headers);
      
      const response = await axios.post(`${API}/simular`, parametros, { headers });
      
      if (response.data.erro) {
        setErro(response.data.mensagem);
        setResultados(null);
      } else {
        setResultados(response.data);
        console.log('✅ Simulação realizada com sucesso');
      }
    } catch (error) {
      console.error('❌ Erro na simulação:', error);
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
      console.log('📄 Iniciando download do relatório PDF...');
      
      const response = await axios.post(`${API}/gerar-relatorio-pdf`, parametros, {
        responseType: 'blob',
        headers: {
          'Accept': 'application/pdf'
        }
      });
      
      console.log('📄 Resposta recebida:', response.status, response.headers['content-type']);
      
      // Verificar se a resposta é válida
      if (response.status !== 200) {
        throw new Error(`Servidor retornou status ${response.status}`);
      }
      
      // Verificar se recebemos um PDF
      const contentType = response.headers['content-type'] || '';
      if (!contentType.includes('application/pdf')) {
        console.error('❌ Tipo de conteúdo inválido:', contentType);
        throw new Error('Resposta não é um PDF válido');
      }
      
      // Verificar se há dados
      if (!response.data || response.data.size === 0) {
        throw new Error('PDF recebido está vazio');
      }
      
      console.log('📄 PDF válido recebido, tamanho:', response.data.size, 'bytes');
      
      // 🔧 CORREÇÃO: Criar blob explicitamente com tipo PDF
      const blob = new Blob([response.data], { 
        type: 'application/pdf' 
      });
      
      console.log('📄 Blob criado, tamanho:', blob.size, 'bytes');
      
      // Nome do arquivo com timestamp
      const timestamp = new Date().toISOString().slice(0, 16).replace(/[:-]/g, '');
      const filename = `relatorio_consorcio_${timestamp}.pdf`;
      
      // 🔧 MÉTODO PRINCIPAL: Download via link temporário
      try {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.style.display = 'none';
        link.href = url;
        link.download = filename;
        link.setAttribute('download', filename);
        
        // Adicionar ao DOM, clicar e remover
        document.body.appendChild(link);
        console.log('📄 Iniciando download via link:', filename);
        
        link.click();
        
        // Cleanup
        setTimeout(() => {
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
          console.log('📄 Download concluído e recursos liberados');
        }, 100);
        
      } catch (linkError) {
        console.warn('⚠️ Método de link falhou, tentando fallback:', linkError);
        
        // 🔧 FALLBACK: Tentar usar window.open
        try {
          const url = window.URL.createObjectURL(blob);
          const newWindow = window.open(url);
          if (newWindow) {
            console.log('📄 PDF aberto em nova janela como fallback');
            setTimeout(() => window.URL.revokeObjectURL(url), 1000);
          } else {
            throw new Error('Pop-up bloqueado');
          }
        } catch (fallbackError) {
          console.error('❌ Todos os métodos de download falharam:', fallbackError);
          throw new Error('Seu navegador bloqueou o download. Tente permitir pop-ups ou usar outro navegador.');
        }
      }
      
    } catch (error) {
      console.error('❌ Erro ao baixar relatório:', error);
      console.error('❌ Detalhes do erro:', error.response?.data || error.message);
      
      // Mostrar erro mais específico
      if (error.response?.status === 400) {
        setErro('Erro nos parâmetros da simulação. Verifique os valores e tente novamente.');
      } else if (error.response?.status === 500) {
        setErro('Erro interno do servidor. Tente novamente em alguns momentos.');
      } else if (error.message.includes('navegador bloqueou')) {
        setErro('Download bloqueado pelo navegador. Verifique as configurações de pop-up ou tente outro navegador.');
      } else {
        setErro(`Erro ao gerar relatório PDF: ${error.message}`);
      }
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
          {/* Header Principal */}
          <div className="flex items-center gap-3 justify-between mb-6">
            <div className="flex items-center gap-3">
              <Calculator className="h-8 w-8 text-accent-warm" />
              <div>
                <h1 className="text-2xl font-bold">Portal de Análise de Consórcio</h1>
                <p className="text-neutral-light opacity-90">Simulações e análises inteligentes para consórcios</p>
              </div>
            </div>
            
            {hasAccess && leadInfo && (
              <div className="text-right flex items-center gap-4">
                <button
                  onClick={() => {
                    const newAdminState = !showAdmin;
                    
                    if (newAdminState) {
                      // Entrando no modo admin - verificar autenticação
                      const isAuthenticated = localStorage.getItem('admin_authenticated') === 'true';
                      
                      // Mudar URL para admin
                      window.location.hash = '#admin';
                      
                      if (isAuthenticated) {
                        setAdminAuthenticated(true);
                        setShowAdmin(true);
                        localStorage.setItem('admin_mode', 'true');
                        console.log('🔧 Entrando no modo admin autenticado');
                      } else {
                        // Não autenticado - será tratado pelo useEffect quando URL mudar
                        console.log('🔐 Redirecionando para tela de login admin');
                      }
                    } else {
                      // 🔧 CORREÇÃO: Saindo do modo admin
                      window.location.hash = '';
                      setShowAdmin(false);
                      localStorage.removeItem('admin_mode');
                      console.log('🔧 Saindo do modo admin');
                    }
                  }}
                  className="flex items-center gap-2 px-3 py-1 bg-accent-warm text-primary-accent rounded text-sm hover:bg-opacity-90"
                >
                  <Settings className="h-4 w-4" />
                  {showAdmin ? 'Simulador' : 'Admin'}
                </button>
                <div>
                  <p className="text-sm text-accent-warm">Bem-vindo, {leadInfo.name}</p>
                  <button 
                    onClick={() => {
                      localStorage.removeItem('access_token');
                      localStorage.removeItem('admin_mode');
                      localStorage.removeItem('admin_authenticated'); // 🔐 Limpar autenticação admin
                      setHasAccess(false);
                      setAccessToken(null);
                      setLeadInfo(null);
                      setShowAdmin(false);
                      setAdminAuthenticated(false);
                      setAdminPassword('');
                      setAdminLoginError('');
                    }}
                    className="text-xs text-neutral-light opacity-75 hover:opacity-100"
                  >
                    Sair
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Abas Principais */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="simulador" className="flex items-center gap-2">
                <Calculator className="h-4 w-4" />
                Simulador
              </TabsTrigger>
              <TabsTrigger value="analise-contrato" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Análise de Contrato
              </TabsTrigger>
            </TabsList>

            {/* Conteúdo das Abas */}
            <TabsContent value="simulador" className="mt-6">
              {/* Todo o conteúdo do simulador atual */}
              <div className="flex items-center gap-3 justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Calculator className="h-6 w-6 text-accent-warm" />
                  <div>
                    <h2 className="text-xl font-bold">Simulador de Consórcio</h2>
                    <p className="text-neutral-light opacity-90">Análise completa de lance livre e fluxos de caixa</p>
                  </div>
                </div>
              </div>
              
              {/* Conteúdo do simulador */}
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

                  {!resultados && !erro && (
                    <Card className="border-moonstone">
                      <CardContent className="p-8 text-center">
                        <Calculator className="h-12 w-12 text-neutral-mid mx-auto mb-4" />
                        <h3 className="text-lg font-semibold text-primary-accent mb-2">
                          Pronto para simular!
                        </h3>
                        <p className="text-neutral-mid text-sm md:text-base">
                          Configure os parâmetros à esquerda e clique em "Simular Consórcio" para ver os resultados.
                        </p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="analise-contrato" className="mt-6">
              <ContractAnalysis />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {!hasAccess && !isAdminAccess ? (
        /* Mostrar tela de Lead Capture */
        <div className="container mx-auto px-4 md:px-6 py-8">
          <CadastroForm onAccessGranted={handleAccessGranted} />
        </div>
      ) : showAdmin || isAdminAccess ? (
        /* 🔐 PROTEÇÃO ADMIN: Mostrar login ou painel conforme autenticação */
        !adminAuthenticated ? (
          /* Tela de Login Admin */
          <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
              <div className="text-center mb-8">
                <div className="mx-auto h-12 w-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
                  <Settings className="h-6 w-6 text-red-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900">Acesso Administrativo</h2>
                <p className="text-gray-600 mt-2">Digite a senha para acessar o painel admin</p>
              </div>
              
              <form onSubmit={(e) => {
                e.preventDefault();
                console.log('🔐 Tentativa de login com senha:', adminPassword);
                const success = handleAdminLogin(adminPassword);
                if (success) {
                  console.log('🔐 Login bem-sucedido, atualizando estado...');
                  // Forçar atualização do estado
                  setTimeout(() => {
                    setShowAdmin(true);
                    localStorage.setItem('admin_mode', 'true');
                  }, 100);
                }
              }}>
                <div className="mb-4">
                  <Label htmlFor="adminPassword" className="block text-sm font-medium text-gray-700 mb-2">
                    Senha de Administrador
                  </Label>
                  <Input
                    id="adminPassword"
                    type="password"
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    className="w-full"
                    placeholder="Digite a senha..."
                    required
                  />
                  {adminLoginError && (
                    <p className="mt-2 text-sm text-red-600">{adminLoginError}</p>
                  )}
                </div>
                
                <Button 
                  type="submit"
                  className="w-full bg-red-600 hover:bg-red-700 text-white"
                >
                  Entrar no Admin
                </Button>
              </form>
              
              <div className="mt-6 text-center">
                <button 
                  onClick={() => {
                    setShowAdmin(false);
                    localStorage.removeItem('admin_mode');
                    window.location.hash = '';
                  }}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Voltar ao simulador
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Painel Admin Autenticado */
          <div>
            <div className="bg-white border-b border-gray-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-semibold text-gray-900">Painel Administrativo</h1>
                <button
                  onClick={handleAdminLogout}
                  className="flex items-center gap-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                >
                  Sair do Admin
                </button>
              </div>
            </div>
            <AdminPanel />
          </div>
        )
      ) : (
        /* Conteúdo principal - Simulador quando tem acesso mas não está no admin */
        <div className="container mx-auto px-4 md:px-6 py-8">
          {/* O conteúdo do simulador já está renderizado no header acima */}
        </div>
      )}
    </div>
  );
}

export default App;
