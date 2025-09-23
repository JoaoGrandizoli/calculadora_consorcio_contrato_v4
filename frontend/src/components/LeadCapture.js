import React, { useState } from 'react';
import SimpleForm from './SimpleForm';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);

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

  // Sempre usar o formulário simples - funciona perfeitamente
  return <SimpleForm onAccessGranted={(token) => {
    onAccessGranted(token);
    setShowForm(false);
  }} />;
};

export default LeadCapture;