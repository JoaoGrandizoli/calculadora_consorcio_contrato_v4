import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Users, BarChart3, Download, RefreshCw, Link } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const AdminPanel = () => {
  const [leads, setLeads] = useState([]);
  const [simulations, setSimulations] = useState([]);
  const [dadosCompletos, setDadosCompletos] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchDadosCompletos = async () => {
    try {
      const response = await axios.get(`${API}/api/admin/dados-completos`);
      setDadosCompletos(response.data);
    } catch (error) {
      console.error('Erro ao buscar dados completos:', error);
    }
  };

  const fetchLeads = async () => {
    try {
      const response = await axios.get(`${API}/api/admin/leads`);
      setLeads(response.data.leads || []);
    } catch (error) {
      console.error('Erro ao buscar leads:', error);
    }
  };

  const fetchSimulations = async () => {
    try {
      const response = await axios.get(`${API}/api/admin/simulations`);
      setSimulations(response.data.simulations || []);
    } catch (error) {
      console.error('Erro ao buscar simulações:', error);
    }
  };

  const refreshData = async () => {
    setLoading(true);
    await Promise.all([fetchLeads(), fetchSimulations(), fetchDadosCompletos()]);
    setLoading(false);
  };

  useEffect(() => {
    refreshData();
  }, []);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    
    // Converter para timezone de Brasília (UTC-3)
    const date = new Date(dateString);
    const brasiliaDate = new Date(date.getTime() - (3 * 60 * 60 * 1000)); // UTC-3
    
    return brasiliaDate.toLocaleString('pt-BR', {
      timeZone: 'America/Sao_Paulo',
      day: '2-digit',
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  const exportToCSV = (data, filename) => {
    const csv = [
      Object.keys(data[0] || {}).join(','),
      ...data.map(row => Object.values(row).map(val => 
        typeof val === 'string' && val.includes(',') ? `"${val}"` : val
      ).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            📊 Analytics do Simulador
          </h1>
          <p className="text-gray-600">
            Leads capturados e simulações realizadas com associações
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Users className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Leads</p>
                  <p className="text-2xl font-bold text-gray-900">{leads.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <BarChart3 className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Simulações</p>
                  <p className="text-2xl font-bold text-gray-900">{simulations.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Link className="h-8 w-8 text-purple-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Conversão</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dadosCompletos ? dadosCompletos.resumo.leads_que_simularam : 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <BarChart3 className="h-8 w-8 text-orange-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Sem Cadastro</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dadosCompletos ? dadosCompletos.simulacoes_sem_cadastro.length : 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Navigation Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8">
              <button
                onClick={() => setActiveTab('overview')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'overview'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                📊 Visão Geral
              </button>
              <button
                onClick={() => setActiveTab('leads')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'leads'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                👥 Leads ({leads.length})
              </button>
              <button
                onClick={() => setActiveTab('simulations')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'simulations'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                📈 Simulações ({simulations.length})
              </button>
            </nav>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center mb-6">
          <Button 
            onClick={refreshData} 
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>

          <div className="flex gap-2">
            {activeTab === 'simulations' && simulations.length > 0 && (
              <Button 
                onClick={() => exportToCSV(simulations, 'simulacoes.csv')}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Exportar
              </Button>
            )}
          </div>
        </div>

        {/* Content */}
        <Card>
          <CardContent className="p-0">
            {activeTab === 'overview' && dadosCompletos && (
              <div className="p-6">
                <h3 className="text-lg font-semibold mb-4">🔗 Leads + Simulações Associadas</h3>
                
                {dadosCompletos.leads_com_simulacoes.length > 0 ? (
                  <div className="space-y-4">
                    {dadosCompletos.leads_com_simulacoes.map((item, index) => (
                      <div key={index} className="border rounded-lg p-4 bg-gray-50">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <h4 className="font-semibold">{item.lead.name}</h4>
                            <p className="text-sm text-gray-600">{item.lead.email}</p>
                          </div>
                          <div className="text-right">
                            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                              {item.total_simulacoes} simulações
                            </span>
                          </div>
                        </div>
                        
                        {item.simulacoes.length > 0 && (
                          <div className="border-t pt-3">
                            <p className="text-xs text-gray-500 mb-2">Simulações realizadas:</p>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                              {item.simulacoes.map((sim, simIndex) => (
                                <div key={simIndex} className="bg-white p-2 rounded">
                                  <p>{formatCurrency(sim.valor_carta)}</p>
                                  <p className="text-gray-500">{sim.prazo_meses}m</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">Nenhum lead com simulações ainda</p>
                )}

                {dadosCompletos.simulacoes_sem_cadastro.length > 0 && (
                  <div className="mt-8">
                    <h3 className="text-lg font-semibold mb-4">🔓 Simulações Sem Cadastro</h3>
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      <p className="text-orange-800 mb-2">
                        {dadosCompletos.simulacoes_sem_cadastro.length} usuários pularam o cadastro
                      </p>
                      <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs">
                        {dadosCompletos.simulacoes_sem_cadastro.slice(0, 6).map((sim, index) => (
                          <div key={index} className="bg-white p-2 rounded">
                            <p>{formatCurrency(sim.valor_carta)}</p>
                            <p className="text-gray-500">{sim.prazo_meses}m</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Outras abas mantidas como estavam */}
            {activeTab === 'leads' && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Telefone</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Profissão</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {leads.map((lead) => (
                      <tr key={lead.id}>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{lead.name}</td>
                        <td className="px-6 py-4 text-sm text-gray-500">{lead.email}</td>
                        <td className="px-6 py-4 text-sm text-gray-500">{lead.phone}</td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          {lead.profissao || 'Não informada'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">{formatDate(lead.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {leads.length === 0 && (
                  <div className="text-center py-12">
                    <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">Configure seu Typeform para começar a capturar leads</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'simulations' && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Carta</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prazo</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contemplação</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lance %</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {simulations.map((sim) => (
                      <tr key={sim.id}>
                        <td className="px-6 py-4 text-sm text-gray-500">{formatDate(sim.created_at)}</td>
                        <td className="px-6 py-4 text-sm font-medium">{formatCurrency(sim.valor_carta)}</td>
                        <td className="px-6 py-4 text-sm text-gray-500">{sim.prazo_meses}m</td>
                        <td className="px-6 py-4 text-sm text-gray-500">{sim.mes_contemplacao}º mês</td>
                        <td className="px-6 py-4 text-sm text-gray-500">{(sim.lance_livre_perc * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {simulations.length === 0 && (
                  <div className="text-center py-12">
                    <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">Nenhuma simulação realizada ainda</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminPanel;