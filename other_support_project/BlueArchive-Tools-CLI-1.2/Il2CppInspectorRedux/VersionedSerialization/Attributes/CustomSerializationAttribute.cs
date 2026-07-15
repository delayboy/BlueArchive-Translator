namespace VersionedSerialization.Attributes;

[AttributeUsage(AttributeTargets.Field | AttributeTargets.Property)]
#pragma warning disable CS9113 // Parameter is unread.
public class CustomSerializationAttribute(string methodName, string sizeExpression) : Attribute;
#pragma warning restore CS9113 // Parameter is unread.
