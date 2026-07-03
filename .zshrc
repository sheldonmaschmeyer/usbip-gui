# Set up the prompt

# Path to your oh-my-zsh installation.
export ZSH="/home/ubuntu/.oh-my-zsh"

# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="agnoster"

plugins=(history-search-multi-word)

HISTFILE="/home/ubuntu/.zsh_history"
HISTSIZE=1000
SAVEHIST=1000

source $ZSH/oh-my-zsh.sh

alias vi='vim'
