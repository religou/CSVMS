import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
    cleanup()
    localStorage.clear()
})

class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)
vi.stubGlobal('scrollTo', vi.fn())

const originalGetComputedStyle = window.getComputedStyle.bind(window)

Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
})

Object.defineProperty(window, 'getComputedStyle', {
    writable: true,
    value: vi.fn().mockImplementation((element: Element) => {
        const style = originalGetComputedStyle(element)
        // Ant Design rc-table/rc-util uses getPropertyValue and scrollbarColor
        // which are not supported in JSDOM - provide safe defaults
        return {
            ...style,
            scrollbarColor: '',
            getPropertyValue: (prop: string) => {
                try {
                    return style.getPropertyValue(prop)
                } catch {
                    return ''
                }
            },
        }
    }),
})

Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: vi.fn(),
})