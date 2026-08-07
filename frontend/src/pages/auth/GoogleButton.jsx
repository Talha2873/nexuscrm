import { useEffect, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import toast from 'react-hot-toast';

import { googleLogin } from '@/features/authSlice';
import { GOOGLE_CLIENT_ID } from '@/utils/constants';

const SCRIPT_ID = 'google-identity-services';

/**
 * Renders Google's official button via Google Identity Services. If no client
 * ID is configured the component renders nothing, so the rest of the auth form
 * still works in a plain local setup.
 */
export default function GoogleButton({ label = 'Continue with Google' }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const containerRef = useRef(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return undefined;

    const handleCredential = async (response) => {
      const result = await dispatch(googleLogin(response.credential));
      if (googleLogin.fulfilled.match(result)) {
        toast.success('Signed in with Google');
        navigate('/dashboard', { replace: true });
      } else {
        toast.error(result.payload || 'Google sign-in failed');
      }
    };

    const renderButton = () => {
      if (!window.google?.accounts?.id || !containerRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredential,
      });
      window.google.accounts.id.renderButton(containerRef.current, {
        theme: 'outline',
        size: 'large',
        width: '100%',
        text: label.includes('up') ? 'signup_with' : 'signin_with',
      });
    };

    const existing = document.getElementById(SCRIPT_ID);
    if (existing) {
      renderButton();
      return undefined;
    }

    const script = document.createElement('script');
    script.id = SCRIPT_ID;
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = renderButton;
    document.head.appendChild(script);

    return undefined;
  }, [dispatch, navigate, label]);

  if (!GOOGLE_CLIENT_ID) return null;

  return <Box ref={containerRef} sx={{ display: 'flex', justifyContent: 'center' }} />;
}
