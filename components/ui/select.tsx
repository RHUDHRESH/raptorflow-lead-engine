import * as React from "react"

interface SelectProps {
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
}

interface SelectContentProps {
  children: React.ReactNode
}

interface SelectItemProps {
  value: string
  children: React.ReactNode
}

interface SelectTriggerProps {
  children: React.ReactNode
}

interface SelectValueProps {
  placeholder?: string
}

const SelectContext = React.createContext<{
  value?: string
  onValueChange?: (value: string) => void
} | null>(null)

export const Select: React.FC<SelectProps> = ({ value, onValueChange, children }) => {
  return (
    <SelectContext.Provider value={{ value, onValueChange }}>
      <div className="relative">
        {children}
      </div>
    </SelectContext.Provider>
  )
}

export const SelectTrigger: React.FC<SelectTriggerProps> = ({ children }) => {
  return (
    <div className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm ring-offset-white focus-within:outline-none focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2">
      {children}
    </div>
  )
}

export const SelectValue: React.FC<SelectValueProps> = ({ placeholder }) => {
  const context = React.useContext(SelectContext)
  return <span>{context?.value || placeholder || "Select..."}</span>
}

export const SelectContent: React.FC<SelectContentProps> = ({ children }) => {
  return (
    <div className="absolute top-full z-50 mt-1 max-h-60 min-w-[8rem] overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
      <div className="overflow-auto p-1">
        {children}
      </div>
    </div>
  )
}

export const SelectItem: React.FC<SelectItemProps> = ({ value, children }) => {
  const context = React.useContext(SelectContext)
  return (
    <div
      className="relative flex w-full cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-slate-100 focus:bg-slate-100"
      onClick={() => context?.onValueChange?.(value)}
    >
      {children}
    </div>
  )
}
