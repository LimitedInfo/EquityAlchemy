import ReactGA from 'react-ga4';
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const TRACKING_ID = 'G-TF587MMPS2';

export const initGA = () => {
  ReactGA.initialize(TRACKING_ID);
};

export const trackPageView = (path) => {
  ReactGA.send({ hitType: 'pageview', page: path });
};

export const trackEvent = (category, action, label) => {
  ReactGA.event({
    category: category,
    action: action,
    label: label,
  });
};

export const useGoogleAnalytics = () => {
  const location = useLocation();

  useEffect(() => {
    initGA();
  }, []);

  useEffect(() => {
    trackPageView(location.pathname + location.search);
  }, [location]);
};
