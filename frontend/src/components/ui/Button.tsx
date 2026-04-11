import './ui.css'

type Variant = 'primary' | 'secondary' | 'ghost'

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

export function Button({ variant = 'primary', className = '', ...rest }: Props) {
  return (
    <button
      className={`btn btn--${variant} ${className}`.trim()}
      {...rest}
    />
  )
}
