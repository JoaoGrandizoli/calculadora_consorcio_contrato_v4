import React, { useState } from 'react';
import { Widget } from '@typeform/embed-react';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);
  const typeformId = process.env.REACT_APP_TYPEFORM_ID || 'dN3w60PD';

  const handleTypeformSubmit = (data) => {
    console.log('Typeform submetido:', data);
    
    // Gerar access token
    const accessToken = 'typeform-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    // Salvar no localStorage
    localStorage.setItem('access_token', accessToken);
    
    // Conceder acesso
    onAccessGranted(accessToken);
    setShowForm(false);
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
            style={{ width: '100%', height: '100%' }}
            className="typeform-widget"
          />
        </div>
      </div>
    </div>
  );
};

export default LeadCapture;