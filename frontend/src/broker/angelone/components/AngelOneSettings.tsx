import React, { useState } from 'react';
import { Shield, Key, User, Lock, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, Input, Button } from '../../../components/ui';
import { useAngelAuthStore } from '../store/angelAuth.store';
import { AngelCredentials } from '../types';

export const AngelOneSettings: React.FC = () => {
  const { login, isLoading, error, isAuthenticated } = useAngelAuthStore();
  const [creds, setCreds] = useState<AngelCredentials>({
    client_id: '',
    api_key: '',
    secret_key: '',
    mpin: ''
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(creds);
  };

  if (isAuthenticated) return null;

  return (
    <Card className="mt-6 border-primary/20 bg-primary/5">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary" />
          Angel One Configuration
        </CardTitle>
      </CardHeader>
      <form onSubmit={handleLogin} className="p-6 pt-0 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Client ID (User Code)"
            placeholder="e.g. S123456"
            icon={<User className="w-4 h-4" />}
            value={creds.client_id}
            onChange={(e) => setCreds({ ...creds, client_id: e.target.value })}
            required
          />
          <Input
            label="API Key"
            placeholder="Your SmartAPI Key"
            icon={<Key className="w-4 h-4" />}
            value={creds.api_key}
            onChange={(e) => setCreds({ ...creds, api_key: e.target.value })}
            required
          />
          <Input
            label="Secret Key"
            type="password"
            placeholder="Your API Secret"
            icon={<Lock className="w-4 h-4" />}
            value={creds.secret_key}
            onChange={(e) => setCreds({ ...creds, secret_key: e.target.value })}
            required
          />
          <Input
            label="MPIN"
            type="password"
            maxLength={6}
            placeholder="6-digit MPIN"
            icon={<Shield className="w-4 h-4" />}
            value={creds.mpin}
            onChange={(e) => setCreds({ ...creds, mpin: e.target.value })}
            required
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-danger/10 text-danger text-sm rounded-lg">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <Button 
            type="submit" 
            isLoading={isLoading}
            variant="primary"
          >
            Connect Angel One Account
          </Button>
        </div>
      </form>
    </Card>
  );
};
