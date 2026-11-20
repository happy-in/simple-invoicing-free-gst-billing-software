import { renderToStaticMarkup } from 'react-dom/server';
import { expect, it, vi } from 'vitest';
import EmailHistoryPage from './EmailHistoryPage';

vi.mock('@tanstack/react-query', async (importOriginal) => ({
  ...await importOriginal<typeof import('@tanstack/react-query')>(),
  useQuery: () => ({
    data: {
      page: 1,
      total_pages: 1,
      total: 2,
      items: [
        { id: 7, subject: 'Failed test email', to_email: 'test@example.com', sent_at: '2026-01-01T10:00:00Z', status: 'failed', error_message: 'Test SMTP failure' },
        { id: 8, subject: 'Sent test email', to_email: 'test@example.com', sent_at: '2026-01-01T10:00:00Z', status: 'sent' },
      ],
    },
  }),
}));

it('provides a collapsed native disclosure only for the row with an error', () => {
  const html = renderToStaticMarkup(<EmailHistoryPage />);

  expect(html).toMatch(/<button type="button"[^>]*aria-expanded="false" aria-controls="email-error-7">Show error<\/button>/);
  expect(html).toMatch(/<div id="email-error-7" hidden=""[^>]*>Test SMTP failure<\/div>/);
  expect(html).not.toContain('email-error-8');
});
