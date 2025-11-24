import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from '@/app/dashboard/page';
import * as api from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// Mock customer data
const mockCustomers = [
  {
    id: 'cust-001',
    company_name: 'Acme Corp',
    product_key: 'BASIC-XXXX-YYYY',
    machine_limit: 5,
    valid_days: 365,
    revoked: false,
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'cust-002',
    company_name: 'Tech Solutions',
    product_key: 'PRO-AAAA-BBBB',
    machine_limit: 10,
    valid_days: 365,
    revoked: true,
    created_at: '2024-02-20T14:30:00Z',
  },
];

describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('shows loading spinner initially', () => {
      mockedApi.getCustomers.mockImplementation(() => new Promise(() => {}));
      
      render(<DashboardPage />);
      
      const spinner = document.querySelector('[style*="animation"]');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('With Customer Data', () => {
    beforeEach(() => {
      mockedApi.getCustomers.mockResolvedValue({ customers: mockCustomers });
    });

    it('renders dashboard title', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
      });
    });

    it('renders subtitle', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('License management overview')).toBeInTheDocument();
      });
    });

    it('renders Add Customer button', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add Customer')).toBeInTheDocument();
      });
    });

    it('displays correct total customers stat', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Total Customers')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
      });
    });

    it('displays correct revoked count', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        // Find the stat card with "Revoked" title
        expect(screen.getByText('Revoked')).toBeInTheDocument();
        // Check the count "1" exists (revoked stat value)
        expect(screen.getByText('1')).toBeInTheDocument();
      });
    });

    it('renders Recent Customers section', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Recent Customers')).toBeInTheDocument();
      });
    });

    it('displays customer names in table', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
        expect(screen.getByText('Tech Solutions')).toBeInTheDocument();
      });
    });

    it('displays product keys', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('BASIC-XXXX-YYYY')).toBeInTheDocument();
        expect(screen.getByText('PRO-AAAA-BBBB')).toBeInTheDocument();
      });
    });

    it('shows Active badge for non-revoked customer', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        const activeBadges = screen.getAllByText('Active');
        expect(activeBadges.length).toBeGreaterThan(0);
      });
    });

    it('shows Revoked badge for revoked customer', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        // Multiple "Revoked" texts exist - stat card title and badge
        const revokedElements = screen.getAllByText('Revoked');
        expect(revokedElements.length).toBeGreaterThanOrEqual(2); // stat + badge
      });
    });

    it('renders View all link', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('View all →')).toBeInTheDocument();
      });
    });

    it('links to customer detail page', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        const acmeLink = screen.getByText('Acme Corp').closest('a');
        expect(acmeLink).toHaveAttribute('href', '/customers/cust-001');
      });
    });
  });

  describe('Empty State', () => {
    beforeEach(() => {
      mockedApi.getCustomers.mockResolvedValue({ customers: [] });
    });

    it('shows empty state message when no customers', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('No customers yet')).toBeInTheDocument();
      });
    });

    it('shows Add Your First Customer button in empty state', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add Your First Customer')).toBeInTheDocument();
      });
    });

    it('displays zero in stats when no customers', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        const zeros = screen.getAllByText('0');
        expect(zeros.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API error gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockedApi.getCustomers.mockRejectedValue(new Error('API Error'));
      
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to load customers:', expect.any(Error));
      });
      
      consoleSpy.mockRestore();
    });

    it('shows empty state after API error', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockedApi.getCustomers.mockRejectedValue(new Error('API Error'));
      
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('No customers yet')).toBeInTheDocument();
      });
    });
  });

  describe('Stat Cards', () => {
    beforeEach(() => {
      mockedApi.getCustomers.mockResolvedValue({ customers: mockCustomers });
    });

    it('renders all four stat cards', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Total Customers')).toBeInTheDocument();
        expect(screen.getByText('Active Machines')).toBeInTheDocument();
        expect(screen.getByText('Expiring Soon')).toBeInTheDocument();
        expect(screen.getByText('Revoked')).toBeInTheDocument();
      });
    });

    it('shows "Within 30 days" subtitle for Expiring Soon', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Within 30 days')).toBeInTheDocument();
      });
    });
  });

  describe('Table Headers', () => {
    beforeEach(() => {
      mockedApi.getCustomers.mockResolvedValue({ customers: mockCustomers });
    });

    it('renders all table headers', async () => {
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Company')).toBeInTheDocument();
        expect(screen.getByText('Product Key')).toBeInTheDocument();
        expect(screen.getByText('Machine Limit')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('Created')).toBeInTheDocument();
      });
    });
  });

  describe('API Calls', () => {
    it('calls getCustomers on mount', async () => {
      mockedApi.getCustomers.mockResolvedValue({ customers: [] });
      
      render(<DashboardPage />);
      
      await waitFor(() => {
        expect(mockedApi.getCustomers).toHaveBeenCalledTimes(1);
      });
    });
  });
});