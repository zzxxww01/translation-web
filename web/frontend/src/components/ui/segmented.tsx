import { cn } from "@/lib/utils"

export interface SegmentedOption<T extends string> {
  value: T
  label: React.ReactNode
}

/**
 * 分段切换（胶囊底 + 白色选中块），和文章工作台的版本切换同一个样子。
 * 用在「表格 / 分组」这类二三选一的视图切换上；真正切换内容区的用 Tabs。
 */
export function Segmented<T extends string>({ value, options, onChange, className, label }: {
  value: T
  options: SegmentedOption<T>[]
  onChange: (value: T) => void
  className?: string
  label?: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className={cn("inline-flex h-8 items-center gap-0.5 rounded-full bg-bg-inset p-[3px]", className)}>
      {options.map(option => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          onClick={() => onChange(option.value)}
          className={cn(
            "inline-flex h-full items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-[12.5px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&_svg]:size-3.5",
            option.value === value ? "bg-white text-text-primary shadow-thumb" : "text-text-muted hover:text-text-primary"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
