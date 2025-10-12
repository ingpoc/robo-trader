import { toast } from "@/hooks/use-toast"

export const toastUtils = {
  success: (title: string, description?: string) => {
    return toast({
      title,
      description,
      variant: "success",
    })
  },

  error: (title: string, description?: string) => {
    return toast({
      title,
      description,
      variant: "destructive",
    })
  },

  warning: (title: string, description?: string) => {
    return toast({
      title,
      description,
      variant: "warning",
    })
  },

  info: (title: string, description?: string) => {
    return toast({
      title,
      description,
      variant: "default",
    })
  },
}