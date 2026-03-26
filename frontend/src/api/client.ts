import axios from 'axios';
import { notifications } from '@mantine/notifications';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred';

    let title = 'Request Failed';
    if (status === 404) {
      title = 'Not Found';
    } else if (status === 422) {
      title = 'Validation Error';
    } else if (status === 500) {
      title = 'Server Error';
    } else if (!error.response) {
      title = 'Network Error';
    }

    notifications.show({
      title,
      message:
        typeof message === 'string'
          ? message
          : 'The server returned an unexpected response shape.',
      color: 'red',
      autoClose: 5000,
    });

    return Promise.reject(error);
  },
);

export default apiClient;
