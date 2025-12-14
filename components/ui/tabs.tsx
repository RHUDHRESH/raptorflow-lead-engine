import * as React from "react"

interface TabsProps {
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  className?: string
}

interface TabsListProps {
  children: React.ReactNode
  className?: string
}

interface TabsTriggerProps {
  value: string
  children: React.ReactNode
  className?: string
}

interface TabsContentProps {
  value: string
  children: React.ReactNode
  className?: string
}

const TabsContext = React.createContext<{
  value?: string
  onValueChange?: (value: string) => void
} | null>(null)

export const Tabs: React.FC<TabsProps> = ({ value, onValueChange, children, className = "" }) => {
  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={className}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

export const TabsList: React.FC<TabsListProps> = ({ children, className = "" }) => {
  return (
    <div className={`flex space-x-1 bg-gray-100 p-1 rounded-lg ${className}`}>
      {children}
    </div>
  )
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({ value, children, className = "" }) => {
  const context = React.useContext(TabsContext)
  const isActive = context?.value === value

  return (
    <button
      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
        isActive
          ? 'bg-white text-gray-900 shadow-sm'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
      } ${className}`}
      onClick={() => context?.onValueChange?.(value)}
    >
      {children}
    </button>
  )
}

export const TabsContent: React.FC<TabsContentProps> = ({ value, children, className = "" }) => {
  const context = React.useContext(TabsContext)

  if (context?.value !== value) {
    return null
  }

  return <div className={className}>{children}</div>
}
