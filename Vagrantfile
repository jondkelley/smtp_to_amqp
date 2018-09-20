# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
	config.vm.hostname = "jons-amqp-server"
	config.vm.box = "naphatkrit/rabbitmq"
	#config.vm.network :forwarded_port, guest: 25672, host: 55672
	config.vm.network :forwarded_port, guest: 5672, host: 55672
end
