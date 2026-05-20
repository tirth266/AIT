import React from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle, 
  XCircle, 
  Link, 
  Unlink, 
  RefreshCw,
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import { Badge, Button } from '../../../components/ui';
import { useAngelAuthStore } from '../store/angelAuth.store';

interface AngelOneCardProps {
  onConnect: () => void;
}

export const AngelOneCard: React.FC<AngelOneCardProps> = ({ onConnect }) => {
  const { isAuthenticated, profile, isLoading, logout } = useAngelAuthStore();

  return (
    <div className="flex items-center justify-between p-4 bg-background rounded-lg border border-border hover:border-primary/50 transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-blue-600/10 flex items-center justify-center text-blue-500 font-bold text-xl">
          A1
        </div>
        <div>
          <div className="flex items-center gap-2">
            <p className="font-semibold text-text">Angel One</p>
            {isAuthenticated && (
              <Badge variant="success" size="sm" className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Live
              </Badge>
            )}
          </div>
          {isAuthenticated && profile ? (
            <p className="text-xs text-textMuted flex items-center gap-1 mt-0.5">
              Client: <span className="text-primary">{profile.client_code}</span> • {profile.name}
            </p>
          ) : (
            <p className="text-xs text-textMuted">SmartAPI V2 Integration</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {isAuthenticated ? (
          <>
            <Button variant="ghost" size="sm" title="Refresh Connection">
              <RefreshCw className="w-4 h-4 text-textMuted hover:text-primary" />
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={logout}
              className="border-danger/20 text-danger hover:bg-danger/10"
            >
              <Unlink className="w-4 h-4 mr-2" />
              Disconnect
            </Button>
          </>
        ) : (
          <Button 
            variant="primary" 
            size="sm" 
            onClick={onConnect}
            isLoading={isLoading}
          >
            <Link className="w-4 h-4 mr-2" />
            Connect
          </Button>
        )}
      </div>
    </div>
  );
};
