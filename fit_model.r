#read in the table created by process_shapes.py and fit model parameters (coefs)
data = read.csv("out_data/output.csv")
crit = which(data[,2]!=-9999 & data[,4]!=-9999)
z1 = data[crit,18]+1
stack = cbind(data[crit,1],data[crit,2:5],data[crit,2:5]^2,data[crit,6:17],z1)
colnames(stack) = c("y", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12", "x13", "x14", "x15", "x16", "x17", "x18", "x19", "x20", "z1")
pmod = glm(y~x1+x2+x3+x4+x5+x6+x7+x8+x9+x10+x11+x12+x13+x14+x15+x16+x17+x18+x19+x20+z1, data=stack, family=poisson(link = "log"))
coefs = summary(pmod)$coefficients[,1]
write.csv(coefs,"out_data/coefs.csv")
