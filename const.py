
# -*- coding: utf-8 -*-
# python 3.x
# Filename:const.py
# 定义一个常量类实现常量的功能
# 
# 该类定义了一个方法__setattr()__,和一个异常ConstError, ConstError类继承 
# 自类TypeError. 通过调用类自带的字典__dict__, 判断定义的常量是否包含在字典 
# 中。如果字典中包含此变量，将抛出异常，否则，给新创建的常量赋值。 
# 最后两行代码的作用是把const类注册到sys.modules这个全局字典中。
class Const():
    class ConstError(TypeError): pass

    class ConstCaseError(ConstError): pass

    def __setattr__(self, key, value):
        print()
        if key in self.__dict__.keys():
            # 存在性验证
            raise self.ConstError("Can't change a const variable: '%s'" % key)

        if not key.isupper():
            # 语法规范验证
            raise self.ConstCaseError("Const variable must be combined with upper letters:'%s'" % key)

        self.__dict__[key] = value


