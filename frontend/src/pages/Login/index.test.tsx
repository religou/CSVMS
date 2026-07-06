import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import fc from 'fast-check'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { authService } from '@/services/auth'
import LoginPage from './index'

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key: string) => key,
        i18n: {
            language: 'zh-CN',
            changeLanguage: vi.fn(),
        },
    }),
}))

vi.mock('@/services/auth', () => ({
    authService: {
        login: vi.fn(),
        getMe: vi.fn(),
        register: vi.fn(),
    },
}))

function renderLoginPage() {
    return render(
        <MemoryRouter>
            <LoginPage />
        </MemoryRouter>,
    )
}

describe('LoginPage', () => {
    it('renders only the login form, without any Tabs container or register-related UI', () => {
        renderLoginPage()

        expect(document.querySelector('.ant-tabs')).not.toBeInTheDocument()
        expect(
            screen.queryByPlaceholderText('auth.email'),
        ).not.toBeInTheDocument()
        expect(
            screen.queryByPlaceholderText('auth.fullName'),
        ).not.toBeInTheDocument()
        expect(
            screen.queryByRole('button', { name: 'auth.register' }),
        ).not.toBeInTheDocument()

        expect(screen.getByPlaceholderText('auth.username')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('auth.password')).toBeInTheDocument()
        expect(
            screen.getByRole('button', { name: 'auth.login' }),
        ).toBeInTheDocument()
    })
})

type Action =
    | { type: 'username'; value: string }
    | { type: 'password'; value: string }
    | { type: 'click' }

const actionArbitrary: fc.Arbitrary<Action> = fc.oneof(
    fc.string().map((value): Action => ({ type: 'username', value })),
    fc.string().map((value): Action => ({ type: 'password', value })),
    fc.constant<Action>({ type: 'click' }),
)

describe('LoginPage property tests', () => {
    it(
        // Property 1: Register 方法永不被调用
        // Validates: Requirements 1.3
        'never calls authService.register regardless of the interaction sequence',
        async () => {
            await fc.assert(
                fc.asyncProperty(
                    fc.array(actionArbitrary, { maxLength: 20 }),
                    async actions => {
                        vi.clearAllMocks()
                        renderLoginPage()

                        for (const action of actions) {
                            switch (action.type) {
                                case 'username':
                                    await act(async () => {
                                        fireEvent.change(
                                            screen.getByPlaceholderText(
                                                'auth.username',
                                            ),
                                            { target: { value: action.value } },
                                        )
                                    })
                                    break
                                case 'password':
                                    await act(async () => {
                                        fireEvent.change(
                                            screen.getByPlaceholderText(
                                                'auth.password',
                                            ),
                                            { target: { value: action.value } },
                                        )
                                    })
                                    break
                                case 'click':
                                    await act(async () => {
                                        fireEvent.click(
                                            screen.getByRole('button', {
                                                name: 'auth.login',
                                            }),
                                        )
                                    })
                                    break
                            }
                        }

                        expect(authService.register).toHaveBeenCalledTimes(0)

                        cleanup()
                    },
                ),
                { numRuns: 100 },
            )
        },
        120000,
    )
})
