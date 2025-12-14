import * as React from "react"

interface CardProps {
  children: React.ReactNode
  className?: string
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

interface CardTitleProps {
  children: React.ReactNode
  className?: string
}

interface CardContentProps {
  children: React.ReactNode
  className?: string
}

export const Card: React.FC<CardProps> = ({ children, className = "" }) => {
  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow ${className}`}>
      {children}
    </div>
  )
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className = "" }) => {
  return (
    <div className={`px-6 py-4 border-b border-gray-200 ${className}`}>
      {children}
    </div>
  )
}

export const CardTitle: React.FC<CardTitleProps> = ({ children, className = "" }) => {
  return (
    <h3 className={`text-lg font-medium text-gray-900 ${className}`}>
      {children}
    </h3>
  )
}

export const CardContent: React.FC<CardContentProps> = ({ children, className = "" }) => {
  return (
    <div className={`px-6 py-4 ${className}`}>
      {children}
    </div>
  )
}
