import React, { useState, useEffect } from 'react';
import { Widget } from '@typeform/embed-react';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);
  const typeformId = process.env.REACT_APP_TYPEFORM_ID || 'dN3w60PD';

  useEffect(() => {
    // Verificar se há um token de acesso no localStorage
    const existingToken = localStorage.getItem('access_token');
    if (existingToken) {
      onAccessGranted(existingToken);
      setShowForm(false);
    }
  }, [onAccessGranted]);

  const handleTypeformSubmit = async (data) => {
    console.log('Typeform submetido:', data);
    
    try {
      // Aguardar um pouco para o webhook processar
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Buscar o lead mais recente (que deve ser o que acabou de ser criado pelo webhook)
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/admin/leads`);
      const data_leads = await response.json();
      
      if (data_leads.leads && data_leads.leads.length > 0) {
        // Pegar o lead mais recente (primeiro da lista, assumindo que está ordenado por data)
        const latestLead = data_leads.leads[0];
        const correctToken = latestLead.access_token;
        
        console.log('Token correto do webhook:', correctToken);
        
        // Usar o token correto do webhook
        localStorage.setItem('access_token', correctToken);
        localStorage.setItem('typeform_submission', JSON.stringify({
          formId: data.form_id || typeformId,
          responseId: data.response_id,
          timestamp: new Date().toISOString(),
          leadId: latestLead.id
        }));
        
        // Conceder acesso
        onAccessGranted(correctToken);
      } else {
        // Fallback: usar token temporário
        const tempToken = 'temp-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('access_token', tempToken);
        onAccessGranted(tempToken);
      }
      
      setShowForm(false);
      
    } catch (error) {
      console.error('Erro ao sincronizar token:', error);
      
      // Fallback em caso de erro
      const tempToken = 'temp-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('access_token', tempToken);
      onAccessGranted(tempToken);
      setShowForm(false);
    }
  };

  const handleTypeformReady = () => {
    console.log('Typeform está pronto');
  };

  if (!showForm) {
    return (
      <div className="text-center py-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-green-600 text-4xl mb-3">✅</div>
          <h3 className="text-xl font-semibold text-green-800 mb-2">
            Perfeito!
          </h3>
          <p className="text-green-700">
            Agora você pode usar o simulador de consórcio.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 text-center">
          📋 Cadastro para Acessar o Simulador
        </h2>
        <p className="text-gray-600 text-center mb-4 text-sm">
          Preencha o formulário abaixo para ter acesso gratuito ao simulador
        </p>
        
        <div style={{ height: '500px' }}>
          <Widget
            id={typeformId}
            onSubmit={handleTypeformSubmit}
            onReady={handleTypeformReady}
            style={{ width: '100%', height: '100%' }}
            className="typeform-widget"
            hideHeaders={true}
            hideFooter={false}
          />
        </div>
        
        <div className="text-center mt-4">
          <p className="text-xs text-gray-500">
            🔒 Seus dados estão seguros e protegidos
          </p>
        </div>
      </div>
    </div>
  );
};

export default LeadCapture;