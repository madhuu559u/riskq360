import { useMemo } from 'react';
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Group,
  Text,
  ActionIcon,
  Tooltip,
  Menu,
  UnstyledButton,
  Breadcrumbs,
  Anchor,
  Indicator,
  Transition,
  Kbd,
} from '@mantine/core';
import {
  IconSearch,
  IconSun,
  IconMoon,
  IconBell,
  IconPalette,
  IconCheck,
  IconActivity,
  IconLogout,
  IconTypography,
} from '@tabler/icons-react';
import { useThemeStore, type ThemeName } from '../../stores/themeStore';
import { useConfigStore } from '../../stores/configStore';
import { getAllThemes, getAllFonts, type FontFamily } from '../../themes';
import { SpotlightSearch } from './SpotlightSearch';

/* ========================================================================= */
/* Theme color preview swatches                                              */
/* ========================================================================= */
const THEME_SWATCHES: Record<ThemeName, string> = {
  'electric-blue': '#0176D3',
  'deep-ocean': '#0D9488',
  'forest-health': '#059669',
  'midnight-ai': '#7C3AED',
  'sunrise-warm': '#EA580C',
  'royal-medical': '#7C2D8E',
};

/* ========================================================================= */
/* Top Navigation Bar                                                        */
/* ========================================================================= */
function TopNavBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { theme, isDarkMode, fontFamily, setTheme, toggleDarkMode, setFontFamily } = useThemeStore();
  const { toggleSpotlight } = useConfigStore();
  const allThemes = useMemo(() => getAllThemes(), []);
  const allFonts = useMemo(() => getAllFonts(), []);

  const breadcrumbItems = useMemo(() => {
    const items: { label: string; href: string }[] = [
      { label: 'RiskQ360', href: '/' },
    ];
    const path = location.pathname;
    if (path.startsWith('/charts/') && params.chartId) {
      items.push({ label: 'Charts', href: '/' });
      items.push({
        label: params.chartId.length > 12 ? params.chartId.slice(0, 12) + '...' : params.chartId,
        href: `/charts/${params.chartId}`,
      });
    } else if (path === '/dashboard') {
      items.push({ label: 'Dashboard', href: '/dashboard' });
    } else if (path === '/settings') {
      items.push({ label: 'Settings', href: '/settings' });
    } else if (path === '/') {
      items.push({ label: 'Charts', href: '/' });
    }
    return items;
  }, [location.pathname, params.chartId]);

  return (
    <Box
      component="header"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 200,
        height: 40,
        display: 'flex',
        alignItems: 'center',
        padding: '0 14px',
        background: 'var(--mi-glass-bg)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--mi-glass-border)',
        transition: 'background var(--mi-transition-normal)',
      }}
    >
      {/* Left - Logo */}
      <Group gap={8} style={{ flex: '0 0 auto', cursor: 'pointer' }} onClick={() => navigate('/')}>
        <Box
          style={{
            width: 24,
            height: 24,
            borderRadius: 6,
            background: `linear-gradient(135deg, var(--mi-primary), var(--mi-accent))`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 1px 4px color-mix(in srgb, var(--mi-primary) 30%, transparent)',
          }}
        >
          <IconActivity size={14} color="#FFFFFF" stroke={2.5} />
        </Box>
        <Text
          fw={700}
          size="sm"
          className="gradient-text"
          style={{ letterSpacing: '-0.02em', userSelect: 'none' }}
        >
          RiskQ360
        </Text>
      </Group>

      {/* Divider */}
      <Box style={{ width: 1, height: 20, backgroundColor: 'var(--mi-border)', margin: '0 10px', flexShrink: 0 }} />

      {/* Inline Nav */}
      <Group gap={2} style={{ flexShrink: 0 }}>
        {[
          { path: '/', label: 'Charts' },
          { path: '/dashboard', label: 'Dashboard' },
          { path: '/settings', label: 'Settings' },
        ].map((item) => {
          const isActive = item.path === '/'
            ? location.pathname === '/' || location.pathname.startsWith('/charts/')
            : location.pathname === item.path;
          return (
            <UnstyledButton
              key={item.path}
              onClick={() => navigate(item.path)}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--mi-radius-md)',
                fontSize: 12,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--mi-primary)' : 'var(--mi-text-muted)',
                backgroundColor: isActive ? 'color-mix(in srgb, var(--mi-primary) 8%, transparent)' : 'transparent',
                transition: 'all var(--mi-transition-fast)',
              }}
            >
              {item.label}
            </UnstyledButton>
          );
        })}
      </Group>

      {/* Center - Breadcrumbs */}
      <Box style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
        <Breadcrumbs
          separator="/"
          styles={{
            separator: { color: 'var(--mi-text-muted)', margin: '0 6px' },
          }}
        >
          {breadcrumbItems.map((item, idx) => (
            <Anchor
              key={`${item.href}-${idx}`}
              onClick={(e) => {
                e.preventDefault();
                navigate(item.href);
              }}
              size="sm"
              fw={idx === breadcrumbItems.length - 1 ? 600 : 400}
              style={{
                color: idx === breadcrumbItems.length - 1 ? 'var(--mi-text)' : 'var(--mi-text-muted)',
                textDecoration: 'none',
                transition: 'color var(--mi-transition-fast)',
              }}
            >
              {item.label}
            </Anchor>
          ))}
        </Breadcrumbs>
      </Box>

      {/* Right - Actions */}
      <Group gap={4} style={{ flex: '0 0 auto' }}>
        {/* Search Button */}
        <UnstyledButton
          onClick={toggleSpotlight}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '5px 14px',
            borderRadius: 'var(--mi-radius-full)',
            background: 'color-mix(in srgb, var(--mi-primary) 6%, var(--mi-surface))',
            border: '1px solid color-mix(in srgb, var(--mi-primary) 18%, var(--mi-border))',
            color: 'var(--mi-text-muted)',
            fontSize: 12,
            transition: 'all var(--mi-transition-fast)',
            cursor: 'pointer',
            minWidth: 180,
            height: 30,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
          className="search-trigger"
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 40%, var(--mi-border))';
            e.currentTarget.style.boxShadow = '0 2px 8px color-mix(in srgb, var(--mi-primary) 12%, transparent)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 18%, var(--mi-border))';
            e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
          }}
        >
          <IconSearch size={14} stroke={2} color="var(--mi-primary)" />
          <Text size="xs" style={{ flex: 1, color: 'var(--mi-text-muted)', fontWeight: 500 }}>
            Search anything...
          </Text>
          <Kbd size="xs" style={{ fontSize: 9, padding: '1px 5px', lineHeight: 1.4, opacity: 0.6 }}>/</Kbd>
        </UnstyledButton>

        {/* Theme Selector */}
        <Menu
          shadow="lg"
          width={220}
          position="bottom-end"
          radius="lg"
          transitionProps={{ transition: 'pop-top-right', duration: 200 }}
        >
          <Menu.Target>
            <Tooltip label="Theme">
              <ActionIcon
                size={28}
                radius="md"
                variant="subtle"
                color="gray"
                aria-label="Select theme"
              >
                <IconPalette size={15} stroke={1.8} />
              </ActionIcon>
            </Tooltip>
          </Menu.Target>
          <Menu.Dropdown
            style={{
              backgroundColor: 'var(--mi-surface)',
              borderColor: 'var(--mi-border)',
            }}
          >
            <Menu.Label style={{ color: 'var(--mi-text-muted)' }}>Theme</Menu.Label>
            {allThemes.map((t) => (
              <Menu.Item
                key={t.name}
                onClick={() => setTheme(t.name)}
                leftSection={
                  <Box
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      backgroundColor: THEME_SWATCHES[t.name],
                      border: theme === t.name ? '2px solid var(--mi-text)' : '2px solid transparent',
                      transition: 'border-color var(--mi-transition-fast)',
                    }}
                  />
                }
                rightSection={
                  theme === t.name ? <IconCheck size={14} color="var(--mi-primary)" /> : null
                }
                style={{ color: 'var(--mi-text)' }}
              >
                <Text size="sm" fw={theme === t.name ? 600 : 400}>
                  {t.label}
                </Text>
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>

        {/* Font Selector */}
        <Menu shadow="lg" width={200} position="bottom-end" radius="lg" transitionProps={{ transition: 'pop-top-right', duration: 200 }}>
          <Menu.Target>
            <Tooltip label="Font">
              <ActionIcon size={28} radius="md" variant="subtle" color="gray" aria-label="Select font">
                <IconTypography size={15} stroke={1.8} />
              </ActionIcon>
            </Tooltip>
          </Menu.Target>
          <Menu.Dropdown style={{ backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)' }}>
            <Menu.Label style={{ color: 'var(--mi-text-muted)' }}>Font Family</Menu.Label>
            {allFonts.map((f) => (
              <Menu.Item
                key={f.name}
                onClick={() => setFontFamily(f.name)}
                rightSection={fontFamily === f.name ? <IconCheck size={14} color="var(--mi-primary)" /> : null}
                style={{ color: 'var(--mi-text)' }}
              >
                <Text size="sm" fw={fontFamily === f.name ? 600 : 400} style={{ fontFamily: f.family }}>{f.label}</Text>
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>

        {/* Dark Mode Toggle */}
        <Tooltip label={isDarkMode ? 'Light mode' : 'Dark mode'}>
          <ActionIcon
            size={28}
            radius="md"
            variant="subtle"
            color="gray"
            onClick={toggleDarkMode}
            aria-label="Toggle dark mode"
          >
            {isDarkMode ? <IconSun size={15} stroke={1.8} /> : <IconMoon size={15} stroke={1.8} />}
          </ActionIcon>
        </Tooltip>

        {/* Notifications */}
        <Tooltip label="Notifications">
          <Indicator size={6} color="var(--mi-primary)" offset={3} disabled>
            <ActionIcon
              size={28}
              radius="md"
              variant="subtle"
              color="gray"
              aria-label="Notifications"
            >
              <IconBell size={15} stroke={1.8} />
            </ActionIcon>
          </Indicator>
        </Tooltip>

        {/* Logout */}
        <Tooltip label="Sign out">
          <ActionIcon
            size={28}
            radius="md"
            variant="subtle"
            color="gray"
            aria-label="Sign out"
            onClick={() => {
              sessionStorage.removeItem('riskq360-auth');
              navigate('/login');
            }}
          >
            <IconLogout size={15} stroke={1.8} />
          </ActionIcon>
        </Tooltip>
      </Group>
    </Box>
  );
}

/* ========================================================================= */
/* Main App Layout                                                           */
/* ========================================================================= */
export function AppLayout() {
  const { spotlightOpen, setSpotlightOpen } = useConfigStore();

  return (
    <Box
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--mi-background)',
        transition: 'background-color var(--mi-transition-normal)',
      }}
    >
      <TopNavBar />

      <Box
        component="main"
        style={{
          flex: 1,
          position: 'relative',
          paddingBottom: 0,
          overflow: 'hidden',
        }}
      >
        <Outlet />
      </Box>

      <Transition
        mounted={spotlightOpen}
        transition="fade"
        duration={150}
      >
        {(transitionStyles) => (
          <div style={transitionStyles}>
            <SpotlightSearch
              opened={spotlightOpen}
              onClose={() => setSpotlightOpen(false)}
            />
          </div>
        )}
      </Transition>
    </Box>
  );
}
