import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  TextInput,
  PasswordInput,
  Button,
  Text,
  Group,
  Stack,
  Checkbox,
} from '@mantine/core';
import {
  IconUser,
  IconLock,
  IconActivity,
  IconShieldCheck,
  IconHeartRateMonitor,
  IconStethoscope,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';

const DEMO_USER = 'riskq360';
const DEMO_PASS = 'demo2026';

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = useCallback(() => {
    setError('');
    setLoading(true);
    setTimeout(() => {
      if (
        (username === DEMO_USER && password === DEMO_PASS) ||
        (username === 'admin' && password === 'admin')
      ) {
        sessionStorage.setItem('riskq360-auth', 'true');
        navigate('/');
      } else {
        setError('Invalid credentials. Use riskq360 / demo2026');
      }
      setLoading(false);
    }, 600);
  }, [username, password, navigate]);

  return (
    <Box
      style={{
        minHeight: '100vh',
        display: 'flex',
        background: 'linear-gradient(160deg, #030B1A 0%, #0A2644 30%, #0D3B66 60%, #030B1A 100%)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Radial glow behind logo */}
      <Box
        style={{
          position: 'absolute',
          top: '20%',
          left: '25%',
          width: 700,
          height: 700,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(27,150,255,0.12) 0%, rgba(27,150,255,0.04) 40%, transparent 70%)',
          filter: 'blur(40px)',
          pointerEvents: 'none',
        }}
      />
      {/* Secondary glow */}
      <Box
        style={{
          position: 'absolute',
          bottom: '-10%',
          right: '-5%',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(27,150,255,0.08) 0%, transparent 65%)',
          filter: 'blur(50px)',
          pointerEvents: 'none',
        }}
      />
      {/* Subtle light ray */}
      <Box
        style={{
          position: 'absolute',
          top: 0,
          left: '30%',
          width: 2,
          height: '100%',
          background: 'linear-gradient(to bottom, transparent 0%, rgba(27,150,255,0.06) 30%, rgba(27,150,255,0.03) 60%, transparent 100%)',
          filter: 'blur(20px)',
          transform: 'rotate(-15deg)',
          pointerEvents: 'none',
        }}
      />

      {/* Left panel — branding */}
      <Box
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '60px 40px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
          style={{ maxWidth: 480, textAlign: 'center' }}
        >
          {/* Logo */}
          <Group gap={14} justify="center" mb={32}>
            <Box
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: 'linear-gradient(135deg, #3B82F6, #1B96FF)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 8px 32px rgba(59,130,246,0.4), 0 0 0 1px rgba(59,130,246,0.25)',
              }}
            >
              <IconActivity size={30} color="#fff" stroke={2.5} />
            </Box>
            <Box style={{ textAlign: 'left' }}>
              <Text
                fw={800}
                style={{
                  fontSize: 36,
                  background: 'linear-gradient(135deg, #FFFFFF, #93C5FD, #3B82F6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  lineHeight: 1.1,
                  letterSpacing: '-0.03em',
                }}
              >
                RiskQ360
              </Text>
              <Text size="sm" style={{ color: 'rgba(176,196,222,0.7)', letterSpacing: '0.12em', fontWeight: 600, marginTop: 2, fontSize: 11 }}>
                RISK &middot; QUALITY &middot; INTELLIGENCE
              </Text>
            </Box>
          </Group>

          {/* Tagline */}
          <Text
            fw={600}
            style={{
              fontSize: 22,
              color: 'rgba(240,248,255,0.92)',
              lineHeight: 1.4,
              marginBottom: 12,
            }}
          >
            Risk. Quality. Everything in between.
          </Text>
          <Text
            size="md"
            style={{
              color: 'rgba(176,196,222,0.7)',
              lineHeight: 1.7,
              maxWidth: 420,
              margin: '0 auto 40px',
            }}
          >
            AI-powered risk adjustment and quality intelligence — from chart to code, gap to closure, in one unified platform.
          </Text>

          {/* Feature pills — Salesforce style */}
          <Group gap={12} justify="center">
            {[
              { icon: IconShieldCheck, label: 'HCC Risk Coding' },
              { icon: IconHeartRateMonitor, label: 'Care Gap Analytics' },
              { icon: IconStethoscope, label: 'Clinical Intel' },
            ].map(({ icon: Icon, label }) => (
              <Box
                key={label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 16px',
                  borderRadius: 999,
                  backgroundColor: 'rgba(27,150,255,0.1)',
                  border: '1px solid rgba(27,150,255,0.25)',
                }}
              >
                <Icon size={14} color="#1B96FF" stroke={2} />
                <Text size="xs" fw={600} style={{ color: 'rgba(240,248,255,0.85)' }}>
                  {label}
                </Text>
              </Box>
            ))}
          </Group>
        </motion.div>
      </Box>

      {/* Right panel — login form */}
      <Box
        style={{
          width: 440,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 40,
          position: 'relative',
          zIndex: 1,
        }}
      >
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.4, 0, 0.2, 1] }}
          style={{ width: '100%' }}
        >
          <Box
            style={{
              padding: 32,
              borderRadius: 16,
              backgroundColor: '#0D1F3C',
              border: '1px solid rgba(27,150,255,0.15)',
              boxShadow: '0 24px 64px rgba(0,0,0,0.5), 0 0 80px rgba(27,150,255,0.06)',
            }}
          >
            <Text fw={700} size="lg" mb={4} style={{ color: '#FFFFFF' }}>
              Welcome back
            </Text>
            <Text size="sm" mb={24} style={{ color: 'rgba(176,196,222,0.6)' }}>
              Sign in to continue to RiskQ360
            </Text>

            <Stack gap={14}>
              <TextInput
                label="Username"
                placeholder="riskq360"
                leftSection={<IconUser size={15} stroke={1.8} color="#5B9BD5" />}
                value={username}
                onChange={(e) => setUsername(e.currentTarget.value)}
                size="md"
                styles={{
                  label: { color: '#B0C4DE', fontSize: 12, fontWeight: 600, marginBottom: 4 },
                  input: {
                    backgroundColor: '#0A2040',
                    borderColor: 'rgba(27,150,255,0.2)',
                    color: '#FFFFFF',
                    borderRadius: 8,
                    height: 42,
                    '&:focus': { borderColor: '#1B96FF' },
                  },
                }}
              />
              <PasswordInput
                label="Password"
                placeholder="Enter your password"
                leftSection={<IconLock size={15} stroke={1.8} color="#5B9BD5" />}
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
                size="md"
                onKeyDown={(e) => { if (e.key === 'Enter') handleLogin(); }}
                styles={{
                  label: { color: '#B0C4DE', fontSize: 12, fontWeight: 600, marginBottom: 4 },
                  input: {
                    backgroundColor: '#0A2040',
                    borderColor: 'rgba(27,150,255,0.2)',
                    color: '#FFFFFF',
                    borderRadius: 8,
                    height: 42,
                  },
                  innerInput: { color: '#FFFFFF' },
                }}
              />

              <Group justify="space-between">
                <Checkbox
                  label="Remember me"
                  checked={remember}
                  onChange={(e) => setRemember(e.currentTarget.checked)}
                  size="xs"
                  styles={{
                    label: { color: 'rgba(176,196,222,0.6)', fontSize: 12 },
                    input: { backgroundColor: '#0A2040', borderColor: 'rgba(27,150,255,0.3)' },
                  }}
                />
                <Text
                  size="xs"
                  style={{ color: '#1B96FF', cursor: 'pointer', fontWeight: 500 }}
                >
                  Forgot password?
                </Text>
              </Group>

              {error && (
                <Text size="xs" style={{ color: '#f87171', textAlign: 'center' }}>
                  {error}
                </Text>
              )}

              <Button
                fullWidth
                size="md"
                loading={loading}
                onClick={handleLogin}
                style={{
                  backgroundColor: '#1B96FF',
                  border: 'none',
                  borderRadius: 8,
                  fontWeight: 700,
                  height: 44,
                  color: '#FFFFFF',
                  boxShadow: '0 4px 20px rgba(27,150,255,0.3)',
                  marginTop: 4,
                  transition: 'background-color 0.15s ease',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#0176D3'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#1B96FF'; }}
              >
                Sign In
              </Button>
            </Stack>

            <Text
              size="xs"
              ta="center"
              mt={20}
              style={{ color: 'rgba(176,196,222,0.35)' }}
            >
              Demo: riskq360 / demo2026
            </Text>
          </Box>

          {/* Footer */}
          <Text
            size="xs"
            ta="center"
            mt={20}
            style={{ color: 'rgba(176,196,222,0.35)' }}
          >
            &copy; 2026 RiskQ360 &middot; Risk &middot; Quality &middot; Intelligence
          </Text>
        </motion.div>
      </Box>
    </Box>
  );
}
